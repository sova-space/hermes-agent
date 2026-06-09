"""
Hermes Agent — Railway launcher.

Starts ``hermes gateway`` and ``hermes dashboard`` as subprocesses,
reverse-proxies the native dashboard to ``$PORT``.  All configuration
is managed through Railway env vars and Hermes native CLI / dashboard.

Key env vars:
  LLM_MODEL          — model.default in config.yaml
  PROVIDER           — model.provider in config.yaml (default: "auto")
  HERMES_HOME        — root directory (default: ~/.hermes)
  PORT               — listening port (default: 8080)
  HERMES_DASHBOARD_PORT — dashboard port on loopback (default: 9119)
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import signal
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import websockets
import websockets.exceptions
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

log = logging.getLogger("server")
logging.basicConfig(level=logging.INFO, format="[server] %(message)s")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
ENV_FILE = HERMES_HOME / ".env"
CONFIG_FILE = HERMES_HOME / "config.yaml"

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = int(os.environ.get("HERMES_DASHBOARD_PORT", "9119"))
DASHBOARD_URL = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"

HOP_BY_HOP = frozenset({"host", "transfer-encoding"})
STRIP_RESP = frozenset({"content-encoding", "content-length"})


def read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        out[k.strip()] = v
    return out


def build_env() -> dict[str, str]:
    """os.environ merged with .env overrides."""
    env = dict(os.environ)
    env["HERMES_HOME"] = str(HERMES_HOME)
    env.update(read_dotenv(ENV_FILE))
    return env


def sync_model_config(model: str, provider: str) -> None:
    """Write model.default + model.provider, preserving existing config."""
    import yaml
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if CONFIG_FILE.exists():
        try:
            loaded = yaml.safe_load(CONFIG_FILE.read_text())
            if isinstance(loaded, dict):
                existing = loaded
        except yaml.YAMLError:
            log.warning("config.yaml unparseable, overwriting")
    merged = dict(existing)
    ms = dict(merged.get("model", {}) if isinstance(merged.get("model"), dict) else {})
    if model:
        ms["default"] = model
    ms["provider"] = provider
    merged["model"] = ms

    # Auto-configure auxiliary providers so context compression, vision, etc.
    # work without the "No auxiliary LLM provider configured" warning.
    aux_defaults = {
        "vision": "openrouter",
        "compression": "openrouter",
        "web_extract": "openrouter",
        "approval": "openrouter",
        "title_generation": "openrouter",
    }
    aux = dict(merged.get("auxiliary", {}) if isinstance(merged.get("auxiliary"), dict) else {})
    for task, aux_provider in aux_defaults.items():
        task_cfg = dict(aux.get(task, {}) if isinstance(aux.get(task), dict) else {})
        task_cfg.setdefault("provider", aux_provider)
        aux[task] = task_cfg
    merged["auxiliary"] = aux

    # Cap max_tokens for free-tier providers to avoid 402 credit errors.
    # openrouter/auto may route to free models — always set a safe default.
    if provider == "openrouter" and (model in ("openrouter/auto",) or "free" in model):
        ms.setdefault("max_tokens", 4096)

    CONFIG_FILE.write_text(yaml.safe_dump(merged, sort_keys=False, default_flow_style=False))


# ---------------------------------------------------------------------------
# Subprocess
# ---------------------------------------------------------------------------
class Subprocess:
    def __init__(self, name: str, log_lines: int = 500):
        self.name = name
        self.proc: asyncio.subprocess.Process | None = None
        self.logs: deque[str] = deque(maxlen=log_lines)
        self.started_at: float | None = None
        self.restarts = 0
        self._state = "stopped"

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        self._state = value

    async def _drain(self) -> None:
        assert self.proc and self.proc.stdout
        try:
            async for raw in self.proc.stdout:
                line = ANSI_RE.sub("", raw.decode(errors="replace").rstrip())
                self.logs.append(f"[{self.name}] {line}")
                print(f"[{self.name}] {line}", flush=True)
        except Exception as exc:
            log.warning("%s drain error: %s", self.name, exc)

    async def stop(self) -> None:
        if not self.proc or self.proc.returncode is not None:
            self._state = "stopped"
            return
        self._state = "stopping"
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=10)
        except asyncio.TimeoutError:
            self.proc.kill()
            await self.proc.wait()
        self._state = "stopped"


class Gateway(Subprocess):
    def __init__(self):
        super().__init__("gateway")

    async def start(self) -> None:
        if self.proc and self.proc.returncode is None:
            return
        self._state = "starting"
        env = build_env()
        model = env.get("LLM_MODEL", "")
        provider = env.get("PROVIDER", "auto")
        log.info("gateway model=%s provider=%s", model or "NOT SET", provider)
        sync_model_config(model, provider)
        try:
            self.proc = await asyncio.create_subprocess_exec(
                "hermes", "gateway",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            self._state = "running"
            self.started_at = __import__("time").time()
            asyncio.create_task(self._drain())
        except Exception as exc:
            self._state = "error"
            self.logs.append(f"[gateway] failed: {exc}")


class Dashboard(Subprocess):
    def __init__(self):
        super().__init__("dashboard", log_lines=300)

    async def start(self) -> None:
        if self.proc and self.proc.returncode is None:
            return
        try:
            self.proc = await asyncio.create_subprocess_exec(
                "hermes", "dashboard",
                "--host", DASHBOARD_HOST,
                "--port", str(DASHBOARD_PORT),
                "--no-open", "--skip-build", "--tui",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            log.info("dashboard spawned pid=%s", self.proc.pid)
            asyncio.create_task(self._drain())
        except Exception as exc:
            log.error("dashboard failed: %s", exc)


gateway = Gateway()
dashboard = Dashboard()


# ---------------------------------------------------------------------------
# HTTP proxy
# ---------------------------------------------------------------------------
_http: httpx.AsyncClient | None = None

def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0), follow_redirects=False)
    return _http


async def _proxy(request: Request) -> Response:
    url = f"{DASHBOARD_URL}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    body = await request.body()
    try:
        upstream = await _client().request(request.method, url, headers=headers, content=body)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return HTMLResponse("", status_code=503)
    except httpx.RequestError:
        return HTMLResponse("", status_code=502)
    resp_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in HOP_BY_HOP and k.lower() not in STRIP_RESP
    }
    return Response(content=upstream.content, status_code=upstream.status_code, headers=resp_headers)


# ---------------------------------------------------------------------------
# WebSocket proxy
# ---------------------------------------------------------------------------
async def _ws_proxy(ws: WebSocket) -> None:
    url = f"ws://{DASHBOARD_HOST}:{DASHBOARD_PORT}{ws.url.path}"
    if ws.url.query:
        url = f"{url}?{ws.url.query}"
    try:
        upstream = await websockets.connect(url, open_timeout=5)
    except Exception:
        await ws.close(code=1011)
        return
    await ws.accept()

    async def pump_in() -> None:
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    return
                data = msg.get("bytes") or msg.get("text")
                if data is not None:
                    await upstream.send(data)
        except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
            pass

    async def pump_out() -> None:
        try:
            async for msg in upstream:
                if isinstance(msg, bytes):
                    await ws.send_bytes(msg)
                else:
                    await ws.send_text(msg)
        except (websockets.exceptions.ConnectionClosed, WebSocketDisconnect):
            pass

    tasks = (asyncio.create_task(pump_in()), asyncio.create_task(pump_out()))
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    try:
        await upstream.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
async def _health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "gateway": gateway.state})


ALL_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

app = Starlette(lifespan=None, routes=[
    Route("/health", _health),
    Route("/", _proxy, methods=ALL_METHODS),
    Route("/{path:path}", _proxy, methods=ALL_METHODS),
    WebSocketRoute("/api/pty", _ws_proxy),
    WebSocketRoute("/api/ws", _ws_proxy),
    WebSocketRoute("/api/events", _ws_proxy),
])


@asynccontextmanager
async def lifespan(application):
    asyncio.create_task(dashboard.start())
    asyncio.create_task(gateway.start())
    try:
        yield
    finally:
        await asyncio.gather(gateway.stop(), dashboard.stop(), return_exceptions=True)
        global _http
        if _http is not None:
            await _http.aclose()
            _http = None


app.router.lifespan_context = lifespan


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    cfg = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info", loop="asyncio")
    srv = uvicorn.Server(cfg)

    def _on_signal() -> None:
        loop.create_task(gateway.stop())
        loop.create_task(dashboard.stop())
        srv.should_exit = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _on_signal)

    loop.run_until_complete(srv.serve())

"""
Hermes Agent — Railway launcher.

Starts hermes gateway + dashboard as subprocesses, reverse-proxies
the native Hermes dashboard to $PORT.  No setup wizard, no OAuth
flows, no cookie auth — config is managed via Hermes CLI / env vars.
"""
import asyncio
import os
import re
import signal
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import websockets
import websockets.exceptions
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

HERMES_HOME = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
ENV_FILE = Path(HERMES_HOME) / ".env"

# Native Hermes dashboard — bound to loopback, fronted by reverse proxy
HERMES_DASHBOARD_HOST = "127.0.0.1"
HERMES_DASHBOARD_PORT = int(os.environ.get("HERMES_DASHBOARD_PORT", "9119"))
HERMES_DASHBOARD_URL = f"http://{HERMES_DASHBOARD_HOST}:{HERMES_DASHBOARD_PORT}"

HOP_BY_HOP = {"host", "transfer-encoding"}


# Helpers
def _read_env(path: Path) -> dict[str, str]:
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


def _write_model_config(model: str, provider: str) -> None:
    """Write just model.default + model.provider to config.yaml, preserving
    the rest of the file (user-managed keys like mcp_servers, telegram, etc.)."""
    import yaml
    config_path = Path(HERMES_HOME) / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if config_path.exists():
        try:
            with config_path.open() as f:
                loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            pass
    merged = dict(existing)
    merged_model = dict(merged.get("model") if isinstance(merged.get("model"), dict) else {})
    if model:
        merged_model["default"] = model
    merged_model["provider"] = provider
    merged["model"] = merged_model
    with config_path.open("w") as f:
        yaml.safe_dump(merged, f, sort_keys=False, default_flow_style=False)


# ---------------------------------------------------------------------------
# Gateway subprocess
# ---------------------------------------------------------------------------
class Gateway:
    def __init__(self):
        self.proc: asyncio.subprocess.Process | None = None
        self.state = "stopped"
        self.logs: deque[str] = deque(maxlen=500)
        self.started_at: float | None = None
        self.restarts = 0

    async def start(self):
        if self.proc and self.proc.returncode is None:
            return
        self.state = "starting"
        try:
            env = {**os.environ, "HERMES_HOME": HERMES_HOME}
            env.update(_read_env(ENV_FILE))
            model = env.get("LLM_MODEL", "")
            provider = env.get("PROVIDER", "auto")
            print(
                f"[gateway] model={model or 'NOT SET'} | provider={provider}",
                flush=True,
            )
            # Write minimal config so hermes picks up model + provider
            _write_model_config(model, provider)
            self.proc = await asyncio.create_subprocess_exec(
                "hermes", "gateway",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            self.state = "running"
            self.started_at = time.time()
            asyncio.create_task(self._drain())
        except Exception as e:
            self.state = "error"
            self.logs.append(f"[error] Failed to start gateway: {e}")

    async def stop(self):
        if not self.proc or self.proc.returncode is not None:
            self.state = "stopped"
            return
        self.state = "stopping"
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=10)
        except TimeoutError:
            self.proc.kill()
            await self.proc.wait()
        self.state = "stopped"
        self.started_at = None

    async def restart(self):
        await self.stop()
        self.restarts += 1
        await self.start()

    async def _drain(self):
        assert self.proc and self.proc.stdout
        async for raw in self.proc.stdout:
            line = ANSI_ESCAPE.sub("", raw.decode(errors="replace").rstrip())
            self.logs.append(line)
        if self.state == "running":
            self.state = "error"
            self.logs.append(f"[error] Gateway exited (code {self.proc.returncode})")


gw = Gateway()


# ---------------------------------------------------------------------------
# Dashboard subprocess
# ---------------------------------------------------------------------------
class Dashboard:
    def __init__(self):
        self.proc: asyncio.subprocess.Process | None = None
        self.logs: deque[str] = deque(maxlen=300)

    async def start(self):
        if self.proc and self.proc.returncode is None:
            return
        try:
            self.proc = await asyncio.create_subprocess_exec(
                "hermes", "dashboard",
                "--host", HERMES_DASHBOARD_HOST,
                "--port", str(HERMES_DASHBOARD_PORT),
                "--no-open", "--skip-build", "--tui",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            print(f"[dashboard] spawned pid={self.proc.pid} -> {HERMES_DASHBOARD_URL}", flush=True)
            asyncio.create_task(self._drain())
        except Exception as e:
            print(f"[dashboard] FAILED to spawn: {e!r}", flush=True)

    async def _drain(self):
        assert self.proc and self.proc.stdout
        try:
            async for raw in self.proc.stdout:
                line = ANSI_ESCAPE.sub("", raw.decode(errors="replace").rstrip())
                self.logs.append(line)
                print(f"[dashboard] {line}", flush=True)
        except Exception as e:
            print(f"[dashboard] drain error: {e!r}", flush=True)
        finally:
            rc = self.proc.returncode if self.proc else None
            if rc is not None and rc != 0:
                print(f"[dashboard] EXITED with code {rc}", flush=True)

    async def stop(self):
        if not self.proc or self.proc.returncode is not None:
            return
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=5)
        except TimeoutError:
            self.proc.kill()
            await self.proc.wait()


dash = Dashboard()


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------
async def route_health(request: Request):
    return JSONResponse({"status": "ok", "gateway": gw.state})


async def route_root(request: Request):
    return await _proxy_to_dashboard(request)


async def route_proxy(request: Request):
    return await _proxy_to_dashboard(request)


DASHBOARD_UNAVAILABLE_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard starting...</title>
<style>body{{background:#0d0f14;color:#c9d1d9;font-family:ui-monospace,monospace;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{max-width:480px;padding:32px;border:1px solid #252d3d;border-radius:12px;
background:#14181f;text-align:center}}
h1{{font-size:16px;color:#d29922;margin:0 0 12px}}
p{{font-size:13px;color:#6b7688;line-height:1.6}}</style></head>
<body><div class="card">
<h1>Hermes dashboard loading...</h1>
<p>Refreshing in a few seconds.</p>
</div>
<script>setTimeout(()=>location.reload(),3000);</script>
</body></html>"""

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=False,
        )
    return _http_client


async def _proxy_to_dashboard(request: Request) -> Response:
    client = get_http_client()
    target = f"{HERMES_DASHBOARD_URL}{request.url.path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    req_headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in HOP_BY_HOP}
    body = await request.body()

    try:
        upstream = await client.request(request.method, target,
                                        headers=req_headers, content=body)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return HTMLResponse(DASHBOARD_UNAVAILABLE_HTML, status_code=503)
    except httpx.RequestError:
        return HTMLResponse(DASHBOARD_UNAVAILABLE_HTML, status_code=502)

    resp_headers = {k: v for k, v in upstream.headers.items()
                    if k.lower() not in HOP_BY_HOP
                    and k.lower() not in ("content-encoding", "content-length")}

    return Response(content=upstream.content,
                    status_code=upstream.status_code,
                    headers=resp_headers)


# WebSocket proxy (for dashboard Chat tab / TUI)
async def ws_proxy(websocket: WebSocket) -> None:
    path = websocket.url.path
    qs = websocket.url.query
    upstream_url = f"ws://{HERMES_DASHBOARD_HOST}:{HERMES_DASHBOARD_PORT}{path}"
    if qs:
        upstream_url = f"{upstream_url}?{qs}"

    try:
        upstream = await websockets.connect(upstream_url, open_timeout=5)
    except Exception:
        await websocket.close(code=1011)
        return

    await websocket.accept()

    async def pump_in():
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.disconnect":
                    return
                data = msg.get("bytes") or msg.get("text")
                if data is not None:
                    await upstream.send(data)
        except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
            pass

    async def pump_out():
        try:
            async for msg in upstream:
                if isinstance(msg, bytes):
                    await websocket.send_bytes(msg)
                else:
                    await websocket.send_text(msg)
        except (websockets.exceptions.ConnectionClosed, WebSocketDisconnect):
            pass

    pump_in_task = asyncio.create_task(pump_in())
    pump_out_task = asyncio.create_task(pump_out())
    done, pending = await asyncio.wait(
        (pump_in_task, pump_out_task), return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    try:
        await upstream.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(dash.start())
    asyncio.create_task(gw.start())
    try:
        yield
    finally:
        await asyncio.gather(gw.stop(), dash.stop(), return_exceptions=True)
        global _http_client
        if _http_client is not None:
            await _http_client.aclose()
            _http_client = None


routes = [
    Route("/health", route_health),
    Route("/", route_root, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]),
    Route("/{path:path}", route_proxy, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]),
    WebSocketRoute("/api/pty", ws_proxy),
    WebSocketRoute("/api/ws", ws_proxy),
    WebSocketRoute("/api/events", ws_proxy),
]

app = Starlette(routes=routes, lifespan=lifespan)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    config = uvicorn.Config(app, host="0.0.0.0", port=port,
                            log_level="info", loop="asyncio")
    server = uvicorn.Server(config)

    def _shutdown():
        loop.create_task(gw.stop())
        loop.create_task(dash.stop())
        server.should_exit = True

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown)

    loop.run_until_complete(server.serve())

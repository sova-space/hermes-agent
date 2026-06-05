---
name: best-practices
description: Python best practices for bots/finance — async rules, charts, APScheduler→bot messaging, Claude tool loop.
version: 1.2.0
---

## Async rules

Never `time.sleep` or blocking I/O inside `async def` — freezes the event loop and blocks Telegram polling.

```python
# blocking call (matplotlib, file I/O) → offload
chart_path = await asyncio.to_thread(charts.pie_by_category, data)
```

## Charts

```python
import matplotlib
matplotlib.use("Agg")  # must be set before pyplot import
import matplotlib.pyplot as plt

# save to tmp, return path, caller cleans up
with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
    plt.savefig(f.name, bbox_inches="tight")
    return f.name
```

Always `os.unlink(path)` after sending. `matplotlib` is not thread-safe — generate in a single thread.

## APScheduler → bot (sync thread → async bot)

```python
# capture loop at lifespan startup
loop = asyncio.get_event_loop()

# inside scheduler job (sync thread)
asyncio.run_coroutine_threadsafe(
    application.bot.send_message(chat_id=..., text=..., message_thread_id=...),
    loop
)
```

## Claude tool use loop

```python
while response.stop_reason == "tool_use":
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = dispatch(block.name, block.input, session)
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
    messages += [{"role": "assistant", "content": response.content}, {"role": "user", "content": tool_results}]
    response = client.messages.create(model=..., tools=TOOLS, messages=messages)
```

Tool results must be `json.dumps`-serialized — no SQLModel objects.

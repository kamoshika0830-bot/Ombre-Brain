#!/usr/bin/env python3
import os
import json
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER = os.environ.get("TELEGRAM_ALLOWED_USER", "")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

session_id: str | None = None

TOOL_EMOJI = {
    "breath": "🧠",
    "hold": "💾",
    "grow": "📝",
    "dream": "💭",
    "trace": "✏️",
    "pulse": "📊",
}


def _tool_label(name: str) -> str:
    short = name.split("__")[-1] if "__" in name else name
    emoji = TOOL_EMOJI.get(short, "🔧")
    return f"{emoji} {short}"


async def _readlines(stream):
    buf = b""
    while True:
        chunk = await stream.read(1024 * 1024)  # 1MB chunks, bypasses 64KB readline limit
        if not chunk:
            if buf.strip():
                yield buf
            break
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line.strip():
                yield line


async def _keep_typing(bot, chat_id: int, stop: asyncio.Event):
    while not stop.is_set():
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global session_id
    user = update.effective_user

    logger.info(f"msg from id={user.id} username={user.username!r}, ALLOWED={ALLOWED_USER!r}")
    if ALLOWED_USER and str(user.id) != ALLOWED_USER and user.username != ALLOWED_USER:
        logger.info("blocked")
        return

    text = update.message.text
    chat_id = update.effective_chat.id

    cmd = [
        "claude", "-p", text,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]
    if session_id:
        cmd += ["--resume", session_id]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=PROJECT_DIR,
    )

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id, stop_typing))

    status_msg = None
    tools_used: list[str] = []
    seen_tool_ids: set[str] = set()
    final_result = ""
    last_text_per_msg: dict[str, str] = {}
    new_sid = session_id

    try:
        async for raw in _readlines(proc.stdout):
            line = raw.decode().strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type", "")

            if etype == "assistant":
                msg = event.get("message", {})
                msg_id = msg.get("id", "")
                content = msg.get("content", [])
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        t = block.get("text", "").strip()
                        if t and msg_id:
                            last_text_per_msg[msg_id] = t
                    elif block.get("type") == "tool_use":
                        tool_id = block.get("id") or block.get("name", "")
                        if tool_id and tool_id not in seen_tool_ids:
                            seen_tool_ids.add(tool_id)
                            label = _tool_label(block.get("name", "?"))
                            tools_used.append(label)
                            status_text = " → ".join(tools_used)
                            if status_msg is None:
                                status_msg = await update.message.reply_text(status_text)
                            else:
                                try:
                                    await status_msg.edit_text(status_text)
                                except Exception:
                                    pass

            elif etype == "result":
                final_result = (event.get("result") or event.get("text") or "").strip()
                new_sid = event.get("session_id") or session_id
                logger.info(f"result event: result={repr(final_result[:80])}, keys={list(event.keys())}")

    finally:
        stop_typing.set()
        typing_task.cancel()
        await proc.wait()

    stderr_out = await proc.stderr.read()
    if stderr_out:
        logger.error(f"claude stderr: {stderr_out.decode()[:300]}")

    session_id = new_sid

    accumulated = "\n".join(last_text_per_msg.values())
    text_to_send = final_result or accumulated
    logger.info(f"final_result={bool(final_result)}, accumulated={bool(accumulated)}, sending={bool(text_to_send)}")
    if not text_to_send:
        return

    for i in range(0, len(text_to_send), 4096):
        await update.message.reply_text(text_to_send[i:i + 4096])


async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global session_id
    user = update.effective_user
    if ALLOWED_USER and str(user.id) != ALLOWED_USER and user.username != ALLOWED_USER:
        return
    session_id = None
    await update.message.reply_text("换窗了。")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("reset", handle_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info(f"Jarvis Telegram bridge starting (project: {PROJECT_DIR})")
    app.run_polling()


if __name__ == "__main__":
    main()

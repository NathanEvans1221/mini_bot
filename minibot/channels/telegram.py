"""Telegram channel — Polling mode, per-user session."""

import asyncio
from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

from minibot.agent.loop import AgentLoop
from minibot.bus.queue import MessageBus
from minibot.providers.base import LLMProvider


class TelegramChannel:
    """Telegram Bot 頻道，使用 Polling 模式接收訊息。"""

    def __init__(
        self,
        bot_token: str,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        memory_window: int = 50,
    ):
        self.bot_token = bot_token
        self.bus = MessageBus()
        self.agent_loop = AgentLoop(
            bus=self.bus,
            provider=provider,
            workspace=workspace,
            model=model,
            max_iterations=max_iterations,
            temperature=temperature,
            max_tokens=max_tokens,
            memory_window=memory_window,
        )

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理 /start 指令。"""
        await update.message.reply_text(
            "🤖 Hi! I'm mini_bot, your personal AI assistant.\n"
            "Send me any message to start chatting!"
        )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理一般文字訊息，每個 User 獨立 Session。"""
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        user_text = update.message.text
        session_key = f"tg:user_{user_id}"

        logger.info("Telegram [{}] {}: {}", session_key, update.effective_user.first_name, user_text)

        try:
            # 呼叫 Agent 處理訊息
            result = await self.agent_loop.process_direct(
                content=user_text,
                session_key=session_key,
            )

            # 回覆（Telegram 訊息上限 4096 字元，超過分段傳送）
            for i in range(0, len(result), 4096):
                await update.message.reply_text(result[i:i + 4096])

        except Exception as e:
            logger.error("Telegram handler error: {}", e)
            await update.message.reply_text("抱歉，處理您的請求時發生錯誤，請稍後再試。")

    def run(self) -> None:
        """啟動 Telegram Bot（Polling 模式）。"""
        # 調大 timeout（預設 5 秒太短，部分網路環境會逾時）
        request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
        app = (
            Application.builder()
            .token(self.bot_token)
            .request(request)
            .build()
        )

        # 註冊 handlers
        app.add_handler(CommandHandler("start", self._handle_start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        logger.info("Telegram Bot started (Polling mode)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

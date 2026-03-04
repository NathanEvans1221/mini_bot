"""Tool registry."""

from typing import Any
from loguru import logger

from minibot.agent.tools.base import Tool


class ToolRegistry:
    """工具登錄表，管理所有可用工具。"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """註冊工具。"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """依名稱取得工具。"""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        """取得所有工具的 schema 定義（供 LLM 使用）。"""
        return [t.to_schema() for t in self._tools.values()]

    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """依名稱執行工具，回傳結果字串。"""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        try:
            return await tool.execute(**params)
        except Exception as e:
            logger.error("Tool execution error: {}", e)
            return "抱歉，執行工具時發生錯誤，請稍後再試。"

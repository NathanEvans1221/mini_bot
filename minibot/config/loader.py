"""Config loading with encryption support."""

import json
import os
import base64
import hashlib
from pathlib import Path
from typing import Any
from cryptography.fernet import Fernet
from minibot.config.schema import Config

_fernet: Fernet | None = None
_encryption_key_env = "MINIBOT_CONFIG_KEY"


def _get_fernet() -> Fernet | None:
    """取得或建立 Fernet 加密實例。"""
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.environ.get(_encryption_key_env)
    if not key:
        return None

    key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
    _fernet = Fernet(key_bytes)
    return _fernet


def _encrypt_value(value: str) -> str:
    """加密敏感值。"""
    fernet = _get_fernet()
    if fernet is None or not value:
        return value
    return fernet.encrypt(value.encode()).decode()


def _decrypt_value(value: str) -> str:
    """解密敏感值。"""
    fernet = _get_fernet()
    if fernet is None or not value:
        return value
    try:
        return fernet.decrypt(value.encode()).decode()
    except Exception:
        return value


def _encrypt_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """加密敏感欄位。"""
    result = data.copy()

    for provider in ["minimax", "openrouter", "anthropic", "openai", "deepseek", "gemini"]:
        if provider in result and isinstance(result[provider], dict):
            if "apiKey" in result[provider] and result[provider]["apiKey"]:
                result[provider]["apiKey"] = _encrypt_value(result[provider]["apiKey"])

    if "channels" in result and isinstance(result.get("channels"), dict):
        telegram = result.get("channels", {}).get("telegram", {})
        if "botToken" in telegram and telegram["botToken"]:
            telegram["botToken"] = _encrypt_value(telegram["botToken"])

    return result


def _decrypt_sensitive_fields(data: dict[str, Any]) -> dict[str, Any]:
    """解密敏感欄位。"""
    result = data.copy()

    for provider in ["minimax", "openrouter", "anthropic", "openai", "deepseek", "gemini"]:
        if provider in result and isinstance(result[provider], dict):
            if "apiKey" in result[provider] and result[provider]["apiKey"]:
                result[provider]["apiKey"] = _decrypt_value(result[provider]["apiKey"])

    if "channels" in result and isinstance(result.get("channels"), dict):
        telegram = result.get("channels", {}).get("telegram", {})
        if "botToken" in telegram and telegram["botToken"]:
            telegram["botToken"] = _decrypt_value(telegram["botToken"])

    return result


def get_config_path() -> Path:
    """取得設定檔路徑（~/.minibot/config.json）。"""
    return Path.home() / ".minibot" / "config.json"


def load_config(config_path: Path | None = None) -> Config:
    """載入設定檔，若不存在則回傳預設值。"""
    path = config_path or get_config_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data = _decrypt_sensitive_fields(data)
            return Config.model_validate(data)
        except Exception as e:
            print(f"Warning: Config load failed: {e}")
    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """儲存設定至磁碟（敏感欄位會加密）。"""
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(by_alias=True)
    data = _encrypt_sensitive_fields(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_encryption_key() -> str:
    """產生新的加密金鑰（供使用者設定環境變數用）。"""
    return Fernet.generate_key().decode()

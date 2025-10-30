#!/usr/bin/env python3
"""
JavDB Manual Login and Cookie Manager
Handles manual login to JavDB and saves cookies for reuse
"""

from __future__ import annotations

"""Manual JavDB cookie manager for semi-automatic scraping."""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class JavDBCookieManager:
    """Persist user-provided JavDB cookies in a JSON file."""

    config_dir: Path = Path("config")
    cookie_filename: str = "javdb_cookies.json"

    def __post_init__(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_path = self.config_dir / self.cookie_filename

    def save_cookie_string(self, cookie_string: str) -> None:
        cookies = self._parse_cookie_string(cookie_string)
        with self.cookie_path.open("w", encoding="utf-8") as fh:
            json.dump(cookies, fh, indent=2, ensure_ascii=False)
        logger.info("Saved JavDB cookies to %s", self.cookie_path)

    def load_cookies(self) -> Dict[str, str]:
        if not self.cookie_path.exists():
            raise FileNotFoundError("未找到已保存的 JavDB Cookie 文件，请先手动输入。")
        with self.cookie_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not data:
            raise ValueError("Cookie 文件格式不正确，需重新输入。")
        return {str(k): str(v) for k, v in data.items()}

    @staticmethod
    def _parse_cookie_string(cookie_string: str) -> Dict[str, str]:
        fragments = cookie_string.split(";")
        cookies: Dict[str, str] = {}
        for fragment in fragments:
            if not fragment.strip():
                continue
            if "=" not in fragment:
                logger.warning("跳过无法解析的 Cookie 片段：%s", fragment)
                continue
            key, value = fragment.split("=", 1)
            cookies[key.strip()] = value.strip()
        if not cookies:
            raise ValueError("未解析到任何有效的 Cookie 键值对。")
        return cookies

    def status(self) -> str:
        if not self.cookie_path.exists():
            return "未找到已保存的 JavDB Cookie。"
        size = self.cookie_path.stat().st_size
        return f"已保存 Cookie 文件：{self.cookie_path} (大小 {size} 字节)"


def interactive_prompt() -> None:
    manager = JavDBCookieManager()
    print("\n请粘贴完整的 JavDB Cookie（单行，格式 name=value; name2=value2 ...）:")
    cookie_string = input("> ").strip()
    if not cookie_string:
        print("❌ 未输入任何内容，操作已取消。")
        return

    try:
        manager.save_cookie_string(cookie_string)
        parsed = manager.load_cookies()
        print("✅ JavDB Cookie 已保存到:", manager.cookie_path)
        print("包含键：", ", ".join(parsed.keys()))
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 保存失败：{exc}")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    interactive_prompt()
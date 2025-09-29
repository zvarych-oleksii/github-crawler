# base.py
import asyncio
import random
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

import aiohttp
from aiohttp.client_exceptions import ClientError, ClientResponseError
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod

from config import REQUEST_TIMEOUT, logger


class BaseCrawler(ABC):
    BASE_URL: str = ""

    def __init__(self, keywords: List[str], proxies: Optional[List[str]] = None):
        self.keywords = keywords
        self.proxies = proxies or []

    @classmethod
    def _make_full_url(cls, path: str) -> str:
        return urljoin(cls.BASE_URL, path)

    async def _get_proxy(self) -> Optional[str]:
        return random.choice(self.proxies) if self.proxies else None

    async def _fetch_html(
        self,
        session: aiohttp.ClientSession,
        url: str,
        proxy: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/webp,*/*;q=0.8"
                ),
            }

            kwargs = {
                "timeout": REQUEST_TIMEOUT,
                "headers": headers,
                "params": params,
            }

            if proxy:
                if "://" not in proxy:
                    proxy = f"http://{proxy}"
                kwargs["proxy"] = proxy
                logger.info("Fetching %s via proxy %s", url, proxy)
            else:
                logger.info("Fetching %s without proxy", url)

            async with session.get(url, **kwargs) as resp:
                resp.raise_for_status()
                logger.info("Response %s from %s", resp.status, url)
                return await resp.text()

        except (asyncio.TimeoutError, ClientError, ClientResponseError) as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

    @abstractmethod
    async def fetch_results(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def _build_url(self) -> str:
        pass

    @abstractmethod
    def _build_params(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def _parse_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        pass

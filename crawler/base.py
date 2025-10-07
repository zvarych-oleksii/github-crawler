import random
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod


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

    async def _make_request(self, session: aiohttp.ClientSession) -> Optional[str]:
        url = await self._build_url()
        params = self._build_params()
        proxy = await self._get_proxy()
        return await self._fetch_html(session, url, proxy, params=params)

    @abstractmethod
    async def _fetch_html(
        self,
        session: aiohttp.ClientSession,
        url: str,
        proxy: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[str]: # pragma: no cover
        pass

    @abstractmethod
    async def fetch_results(self) -> List[Dict[str, Any]]: # pragma: no cover
        pass

    @abstractmethod
    async def _build_url(self) -> str: # pragma: no cover
        pass

    @abstractmethod
    def _build_params(self) -> Dict[str, str]: # pragma: no cover
        pass

    @abstractmethod
    def _parse_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]: # pragma: no cover
        pass

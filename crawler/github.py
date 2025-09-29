import asyncio
import random
from typing import List, Dict, Optional, Any
from enum import Enum
from urllib.parse import urlparse

import aiohttp
from aiohttp.client_exceptions import ClientError, ClientResponseError
from bs4 import BeautifulSoup

from .base import BaseCrawler
from config import GITHUB_BASE_URL, REQUEST_TIMEOUT, logger


class SearchType(str, Enum):
    REPOSITORIES = "Repositories"
    ISSUES = "Issues"
    WIKIS = "Wikis"


class GitHubCrawler(BaseCrawler):
    def __init__(
        self,
        keywords: List[str],
        proxies: Optional[List[str]] = None,
        search_type: SearchType = SearchType.REPOSITORIES,
    ):
        self.keywords = keywords
        self.proxies = proxies or []
        self.search_type = search_type

    @staticmethod
    def _parse_results(soup: BeautifulSoup) -> List[Dict[str, str]]:
        results = []
        for a in soup.select(".search-title a[href^='/']"):
            href = a.get("href", "").strip()
            results.append({"url": f"https://github.com{href}"})
        return results

    async def _get_proxy(self) -> Optional[str]:
        return random.choice(self.proxies) if self.proxies else None

    async def _build_url(self) -> str:
        q = "+".join(self.keywords)
        return f"{GITHUB_BASE_URL}?q={q}&type={self.search_type.value}"

    async def _fetch_html(
            self, session: aiohttp.ClientSession, url: str, proxy: Optional[str] = None
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

            kwargs: Dict[str, Any] = {
                "timeout": REQUEST_TIMEOUT,
                "headers": headers,
            }
            if proxy:
                if "://" not in proxy:
                    proxy = f"http://{proxy}"
                kwargs["proxy"] = proxy
                logger.info(f"Fetching {url} via proxy {proxy}")
            else:
                logger.info(f"Fetching {url} without proxy")

            async with session.get(url, **kwargs) as resp:
                resp.raise_for_status()
                logger.info(f"Response {resp.status} from {url}")
                return await resp.text()

        except (asyncio.TimeoutError, ClientError, ClientResponseError) as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    @staticmethod
    def _extract_owner(repo_url: str) -> str:
        path_parts = urlparse(repo_url).path.strip("/").split("/")
        return path_parts[0] if len(path_parts) >= 2 else ""

    @staticmethod
    def _parse_languages(html: str) -> Dict[str, float]:
        soup = BeautifulSoup(html, "html.parser")
        stats: Dict[str, float] = {}
        lang_items = soup.select("h2:-soup-contains('Languages') ~ ul li")
        if not lang_items:
            lang_items = soup.select("ul.list-style-none li")
        for li in lang_items:
            name_el = li.select_one("span.color-fg-default")
            percent_el = li.select_one("span:not(.color-fg-default)")
            if name_el and percent_el:
                try:
                    stats[name_el.text.strip()] = float(
                        percent_el.text.strip().replace("%", "")
                    )
                except ValueError:
                    continue
        return stats

    async def _extract_languages(
        self, session: aiohttp.ClientSession, repo_url: str, proxy: Optional[str]
    ) -> Dict[str, float]:
        html = await self._fetch_html(session, repo_url, proxy)
        if not html:
            return {}
        return self._parse_languages(html)

    async def fetch_results(self, extra_info: bool = False) -> List[Dict[str, Any]]:
        url = await self._build_url()
        proxy = await self._get_proxy()
        async with aiohttp.ClientSession() as session:
            html = await self._fetch_html(session, url, proxy)
            if not html:
                return []
            soup = BeautifulSoup(html, "html.parser")
            results = self._parse_results(soup)
            if extra_info and self.search_type == SearchType.REPOSITORIES:
                tasks = []
                for item in results:
                    tasks.append(self._enrich_repo(session, item, proxy))
                enriched = await asyncio.gather(*tasks, return_exceptions=True)
                return [r for r in enriched if isinstance(r, dict)]
            return results

    async def _enrich_repo(
        self, session: aiohttp.ClientSession, item: Dict[str, str | Dict[str, Any]], proxy: Optional[str]
    ) -> Dict[str, Any]:
        try:
            owner = self._extract_owner(item["url"])
            language_stats = await self._extract_languages(session, item["url"], proxy)
            item["extra"] = {"owner": owner, "language_stats": language_stats}
            return item
        except Exception as e:
            logger.error(f"Failed to enrich {item['url']}: {e}")
            return item

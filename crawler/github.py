import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, urljoin

import aiohttp
from aiohttp.client_exceptions import ClientError, ClientResponseError
from bs4 import BeautifulSoup

from .base import BaseCrawler
from config import REQUEST_TIMEOUT, logger
from .enums.search_types import SearchType


class GitHubCrawler(BaseCrawler):
    BASE_URL = "https://github.com/"

    def __init__(
        self,
        keywords: List[str],
        proxies: Optional[List[str]] = None,
        search_type: SearchType = SearchType.REPOSITORIES,
    ):
        super().__init__(keywords, proxies)
        self.search_type = search_type

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

    async def _build_url(self) -> str:
        return urljoin(self.BASE_URL, "search")

    def _build_params(self) -> Dict[str, str]:
        return {
            "q": " ".join(self.keywords),
            "type": self.search_type.value,
        }

    def _parse_results(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        results = []
        for a in soup.select(".search-title a[href^='/']"):
            href = a.get("href", "").strip()
            results.append({"url": self._make_full_url(href)})
        return results

    @staticmethod
    def _extract_owner(repo_url: str) -> str:
        path_parts = urlparse(repo_url).path.strip("/").split("/")
        return path_parts[0] if len(path_parts) >= 2 else ""

    @staticmethod
    def _parse_languages(html: str) -> Dict[str, float]:
        soup = BeautifulSoup(html, "html.parser")
        stats = {}
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

    async def _enrich_repo(
        self,
        session: aiohttp.ClientSession,
        item: Dict[str, str | Dict[str, Any]],
        proxy: Optional[str],
    ) -> Dict[str, Any]:
        try:
            owner = self._extract_owner(item["url"])
            language_stats = await self._extract_languages(session, item["url"], proxy)
            item["extra"] = {"owner": owner, "language_stats": language_stats}
            return item
        except Exception as e:
            logger.error("Failed to enrich %s: %s", item["url"], e)
            return item

    async def fetch_results(self, extra_info: bool = False) -> List[Dict[str, Any]]:
        async with aiohttp.ClientSession() as session:
            html = await self._make_request(session)
            if not html:
                return []
            soup = BeautifulSoup(html, "html.parser")
            results = self._parse_results(soup)

            if extra_info and self.search_type == SearchType.REPOSITORIES:
                proxy = await self._get_proxy()
                tasks = [
                    self._enrich_repo(session, item, proxy)
                    for item in results
                ]
                enriched = await asyncio.gather(*tasks, return_exceptions=True)
                return [r for r in enriched if isinstance(r, dict)]

            return results

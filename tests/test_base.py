import pytest
import aiohttp
from bs4 import BeautifulSoup

from crawler.base import BaseCrawler


class DummyCrawler(BaseCrawler):
    BASE_URL = "https://example.com/"

    async def _fetch_html(self, session, url, proxy=None, params=None):
        return "<div class='result'><a href='/repo'>Repo</a></div>"

    async def fetch_results(self):
        async with aiohttp.ClientSession() as session:
            html = await self._make_request(session)
            if not html:
                return []
            soup = BeautifulSoup(html, "html.parser")
            return self._parse_results(soup)

    async def _build_url(self) -> str:
        return "https://example.com/search"

    def _build_params(self):
        return {"q": " ".join(self.keywords)}

    def _parse_results(self, soup: BeautifulSoup):
        results = []
        for a in soup.select("a[href^='/']"):
            href = a.get("href", "").strip()
            results.append({"url": self._make_full_url(href)})
        return results


@pytest.mark.asyncio
async def test_make_full_url():
    assert DummyCrawler._make_full_url("/repo") == "https://example.com/repo"


@pytest.mark.asyncio
async def test_get_proxy_none_and_random(monkeypatch):
    crawler = DummyCrawler(["test"])
    assert await crawler._get_proxy() is None

    crawler_with_proxies = DummyCrawler(["test"], proxies=["p1", "p2"])
    monkeypatch.setattr("random.choice", lambda seq: seq[1])
    proxy = await crawler_with_proxies._get_proxy()
    assert proxy == "p2"


@pytest.mark.asyncio
async def test_make_request_calls_fetch_html(monkeypatch):
    crawler = DummyCrawler(["python"])

    called = {}

    async def fake_fetch_html(session, url, proxy=None, params=None):
        called["url"] = url
        called["params"] = params
        called["proxy"] = proxy
        return "<html></html>"

    crawler._fetch_html = fake_fetch_html

    async with aiohttp.ClientSession() as session:
        html = await crawler._make_request(session)

    assert "html" in html
    assert called["url"] == "https://example.com/search"
    assert called["params"]["q"] == "python"


@pytest.mark.asyncio
async def test_fetch_results_parses_html():
    crawler = DummyCrawler(["test"])

    results = await crawler.fetch_results()
    assert isinstance(results, list)
    assert results[0]["url"] == "https://example.com/repo"


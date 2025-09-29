import pytest
from bs4 import BeautifulSoup
import aiohttp
from aiohttp.client_exceptions import ClientError
from crawler.github import GitHubCrawler, SearchType


@pytest.mark.asyncio
async def test_build_url():
    crawler = GitHubCrawler(["python", "asyncio"], search_type=SearchType.REPOSITORIES)
    url = await crawler._build_url()
    assert "python+asyncio" in url
    assert "type=Repositories" in url


def test_parse_results():
    html = """
    <div class="search-title">
        <a href="/owner1/repo1">Repo1</a>
    </div>
    <div class="search-title">
        <a href="/owner2/repo2">Repo2</a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    results = GitHubCrawler._parse_results(soup)
    assert results == [
        {"url": "https://github.com/owner1/repo1"},
        {"url": "https://github.com/owner2/repo2"},
    ]


def test_extract_owner():
    assert GitHubCrawler._extract_owner("https://github.com/owner1/repo1") == "owner1"
    assert GitHubCrawler._extract_owner("https://github.com/justowner") == ""


def test_parse_languages_basic():
    html = """
    <h2>Languages</h2>
    <ul>
        <li><span class="color-fg-default">Python</span>
            <span>70%</span></li>
        <li><span class="color-fg-default">C++</span>
            <span>30%</span></li>
    </ul>
    """
    stats = GitHubCrawler._parse_languages(html)
    assert stats == {"Python": 70.0, "C++": 30.0}


def test_parse_languages_invalid_and_fallback():
    html = """
    <ul class="list-style-none">
        <li><span class="color-fg-default">Rust</span>
            <span>not-a-number</span></li>
        <li><span class="color-fg-default">Go</span>
            <span>55%</span></li>
    </ul>
    """
    stats = GitHubCrawler._parse_languages(html)
    assert stats == {"Go": 55.0}


@pytest.mark.asyncio
async def test_get_proxy_returns_none_and_random(monkeypatch):
    crawler_empty = GitHubCrawler(["test"])
    assert await crawler_empty._get_proxy() is None

    crawler_with_proxy = GitHubCrawler(["test"], proxies=["http://proxy1", "http://proxy2"])
    monkeypatch.setattr("random.choice", lambda seq: seq[0])
    assert await crawler_with_proxy._get_proxy() == "http://proxy1"


@pytest.mark.asyncio
async def test_fetch_html_success_and_failure(monkeypatch):
    crawler = GitHubCrawler(["test"])

    class DummyResponse:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def text(self): return "<html>ok</html>"
        def raise_for_status(self): return None

    def fake_get(url, **kwargs):
        return DummyResponse()

    async with aiohttp.ClientSession() as session:
        monkeypatch.setattr(session, "get", fake_get)
        html = await crawler._fetch_html(session, "http://fake")
        assert "ok" in html

    def bad_get(url, **kwargs):
        raise ClientError("boom")

    async with aiohttp.ClientSession() as session:
        monkeypatch.setattr(session, "get", bad_get)
        html = await crawler._fetch_html(session, "http://fake")
        assert html is None



@pytest.mark.asyncio
async def test_fetch_results_no_html(monkeypatch):
    crawler = GitHubCrawler(["test"])

    async def mock_fetch_html(*args, **kwargs):
        return None

    monkeypatch.setattr(crawler, "_fetch_html", mock_fetch_html)
    results = await crawler.fetch_results()
    assert results == []


@pytest.mark.asyncio
async def test_fetch_results_with_repos(monkeypatch):
    crawler = GitHubCrawler(["test"], search_type=SearchType.REPOSITORIES)

    html = """
    <div class="search-title">
        <a href="/owner/repo">Repo</a>
    </div>
    """

    async def mock_fetch_html(session, url, proxy):
        return html

    monkeypatch.setattr(crawler, "_fetch_html", mock_fetch_html)

    results = await crawler.fetch_results()
    assert results == [{"url": "https://github.com/owner/repo"}]


@pytest.mark.asyncio
async def test_fetch_results_with_extra_info(monkeypatch):
    crawler = GitHubCrawler(["test"], search_type=SearchType.REPOSITORIES)

    html = """
    <div class="search-title">
        <a href="/owner/repo">Repo</a>
    </div>
    """

    async def mock_fetch_html(session, url, proxy):
        return html

    async def mock_enrich_repo(session, item, proxy):
        item["extra"] = {"owner": "owner", "language_stats": {"Python": 99.0}}
        return item

    monkeypatch.setattr(crawler, "_fetch_html", mock_fetch_html)
    monkeypatch.setattr(crawler, "_enrich_repo", mock_enrich_repo)

    results = await crawler.fetch_results(extra_info=True)
    assert results[0]["extra"]["language_stats"]["Python"] == 99.0


@pytest.mark.asyncio
async def test_enrich_repo_success(monkeypatch):
    crawler = GitHubCrawler(["test"])

    async def mock_extract_languages(session, url, proxy):
        return {"Python": 100.0}

    monkeypatch.setattr(crawler, "_extract_languages", mock_extract_languages)

    item = {"url": "https://github.com/owner/repo"}
    async with aiohttp.ClientSession() as session:
        enriched = await crawler._enrich_repo(session, item, None)

    assert "extra" in enriched
    assert enriched["extra"]["owner"] == "owner"
    assert enriched["extra"]["language_stats"] == {"Python": 100.0}


@pytest.mark.asyncio
async def test_enrich_repo_handles_exception(monkeypatch):
    crawler = GitHubCrawler(["test"])

    async def bad_extract_languages(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(crawler, "_extract_languages", bad_extract_languages)

    item = {"url": "https://github.com/owner/repo"}
    async with aiohttp.ClientSession() as session:
        enriched = await crawler._enrich_repo(session, item, None)

    assert "extra" not in enriched or isinstance(enriched["extra"], dict)

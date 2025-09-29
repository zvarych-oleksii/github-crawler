import json
import asyncio
from pathlib import Path
from crawler.github import GitHubCrawler
from crawler.enums.search_types import SearchType


def main():
    input_file = Path("input_data.json")

    if not input_file.exists():
        raise FileNotFoundError(f"File {input_file} not found")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    keywords = data.get("keywords", [])
    proxies = data.get("proxies", [])
    search_type = data.get("type", "Repositories")
    extra = data.get("extra", True)

    if not keywords:
        raise ValueError("At least one keyword must be specified")

    crawler = GitHubCrawler(keywords, proxies, SearchType(search_type))
    results = asyncio.run(crawler.fetch_results(extra_info=extra))

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

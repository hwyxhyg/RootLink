"""Search public encyclopedia results for regional genealogy context."""

import html
import json
import re

import httpx
from langchain_core.tools import tool


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


@tool
def search_genealogy_location(query: str) -> str:
    """Search public regional history sources for a genealogy location query."""
    language = "zh" if _contains_chinese(query) else "en"
    endpoint = f"https://{language}.wikipedia.org/w/api.php"

    try:
        response = httpx.get(
            endpoint,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 5,
                "format": "json",
                "utf8": 1,
            },
            headers={"User-Agent": "RootLink/1.0 (genealogy research assistant)"},
            timeout=15,
        )
        response.raise_for_status()
        details = []
        for item in response.json().get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            details.append(
                {
                    "title": title,
                    "site_name": "Wikipedia",
                    "url": f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "snippet": html.unescape(snippet),
                }
            )
        return json.dumps(
            {
                "summary": "Public reference results; verify important claims against primary records.",
                "details": details,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps(
            {
                "summary": "",
                "details": [],
                "error": f"地区资料搜索暂时不可用: {exc}",
            },
            ensure_ascii=False,
        )

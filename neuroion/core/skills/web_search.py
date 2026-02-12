"""
Web search skill: search the web for online research.

Use when the user asks to look something up, search the web, or get current information.
Uses DuckDuckGo (no API key required). Optional: SERPAPI_KEY or WEB_SEARCH_API_KEY for other providers.
"""
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from neuroion.core.agent.tool_registry import register_tool

logger = logging.getLogger(__name__)

MAX_RESULTS_DEFAULT = 5
MAX_RESULTS_LIMIT = 15
MAX_SNIPPET_LEN = 300

# Multi-query research: 3 query variations, top 5 per run, merge and dedupe, return up to this many
NUM_SEARCH_ITERATIONS = 3
TOP_PER_ITERATION = 5
MAX_MERGED_RESULTS = 10


def _query_variations(query: str) -> List[str]:
    """Build 3 search query variations for better coverage (original, buy/shop, price)."""
    q = (query or "").strip()
    if not q:
        return []
    lower = q.lower()
    # Prefer NL suffixes if query looks Dutch, else English
    if any(w in lower for w in ("tegels", "tuin", "kopen", "prijs", "zoek", "bestel", "winkel", "nl")):
        return [q, f"{q} kopen", f"{q} prijs aanbieding"]
    return [q, f"{q} buy", f"{q} price"]


def _search_duckduckgo(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Use ddgs/duckduckgo-search package (no API key). Returns list of {title, href, body}."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("ddgs not installed; pip install ddgs")
            return []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        out = []
        for r in results:
            title = (r.get("title") or "")[:200]
            href = r.get("href") or r.get("link") or ""
            body = (r.get("body") or "")[:MAX_SNIPPET_LEN]
            out.append({"title": title, "url": href, "snippet": body})
        return out
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
        return []


@register_tool(
    name="web.search",
    description=(
        "Search the web for current information. Use when the user asks to look something up, "
        "search online, or get recent facts. Runs 3 query variations and returns merged, deduplicated "
        "results (titles, URLs, snippets) for a richer answer."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5, max 15)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)
def web_search(
    db: Session,
    household_id: int,
    query: str,
    max_results: int = MAX_RESULTS_DEFAULT,
) -> Dict[str, Any]:
    """Search the web via DuckDuckGo. Runs 3 query variations, merges top results, dedupes by URL."""
    if not (query or str(query).strip()):
        return {"success": False, "error": "query is required"}
    base_query = str(query).strip()
    # 3 iterations: varied queries, top 5 each, merge and dedupe by URL, cap at max_results
    variations = _query_variations(base_query)
    if not variations:
        return {"success": False, "error": "query is required"}
    seen_urls: set = set()
    merged: List[Dict[str, Any]] = []
    for v in variations[:NUM_SEARCH_ITERATIONS]:
        chunk = _search_duckduckgo(v, TOP_PER_ITERATION)
        for r in chunk:
            url = (r.get("url") or "").strip()
            if not url:
                continue
            norm = url.rstrip("/").lower()
            if norm in seen_urls:
                continue
            seen_urls.add(norm)
            merged.append(r)
            if len(merged) >= MAX_MERGED_RESULTS:
                break
        if len(merged) >= MAX_MERGED_RESULTS:
            break
    cap = min(max(1, max_results), MAX_RESULTS_LIMIT)
    results = merged[:cap]
    if not results:
        return {
            "success": True,
            "query": base_query,
            "results": [],
            "message": "No results or search unavailable. Install ddgs: pip install ddgs",
        }
    return {
        "success": True,
        "query": base_query,
        "results": results,
    }


def _is_safe_url(url: str) -> bool:
    """Allow only http/https URLs, no file or localhost."""
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    if not (u.startswith("http://") or u.startswith("https://")):
        return False
    if "localhost" in u or "127.0.0.1" in u or "file:" in u:
        return False
    return True


@register_tool(
    name="web.fetch_url",
    description=(
        "Fetch the text content of a web page by URL. Use when the user wants to read a specific page or article. "
        "Only http/https URLs; returns first portion of the page text."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL of the page to fetch (http or https only)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default 4000)",
                "default": 4000,
            },
        },
        "required": ["url"],
    },
)
def web_fetch_url(
    db: Session,
    household_id: int,
    url: str,
    max_chars: int = 4000,
) -> Dict[str, Any]:
    """Fetch URL content; sanitized (http/https only, no localhost)."""
    if not (url or str(url).strip()):
        return {"success": False, "error": "url is required"}
    url = str(url).strip()
    if not _is_safe_url(url):
        return {"success": False, "error": "Only http/https URLs allowed; no localhost or file"}
    try:
        import requests
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Neuroion/1.0"})
        resp.raise_for_status()
        text = resp.text
        # Crude strip of script/style and collapse whitespace
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.I)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        return {"success": True, "url": url, "content": text}
    except Exception as e:
        logger.warning("web.fetch_url failed for %s: %s", url, e)
        return {"success": False, "error": str(e)}

"""
GitHub search skill: find repositories by topic, name, or language.

Use when the user asks for a repo, GitHub project, or open-source code.
Uses GitHub REST API (no auth required for public search; rate limit applies).
"""
import logging
from typing import Any, Dict, List

from neuroion.core.agent.tool_registry import register_tool

logger = logging.getLogger(__name__)

MAX_REPOS = 5


@register_tool(
    name="github.search",
    description=(
        "Search GitHub for repositories. Use when the user asks for a repo, "
        "GitHub project, open-source code, or 'zoek repo voor X'. Returns repo name, "
        "URL, and short description. Do not use for general web info—use web.search; "
        "do not use for products—use web.shopping_search."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (topic, language, repo name, or keywords)",
            },
            "max_results": {
                "type": "integer",
                "description": "Max number of repos to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)
def github_search(
    db: Any,
    household_id: int,
    query: str,
    max_results: int = MAX_REPOS,
) -> Dict[str, Any]:
    """Search GitHub repositories via REST API. Returns name, url, description."""
    if not (query or str(query).strip()):
        return {"success": False, "error": "query is required"}
    q = str(query).strip()
    cap = min(max(1, max_results), 10)
    try:
        import requests
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": q, "per_page": cap, "sort": "stars", "order": "desc"},
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("GitHub search failed: %s", e)
        return {"success": False, "error": str(e), "results": []}
    items = data.get("items") or []
    results: List[Dict[str, Any]] = []
    for repo in items[:cap]:
        results.append({
            "name": repo.get("full_name") or repo.get("name") or "",
            "url": repo.get("html_url") or "",
            "description": (repo.get("description") or "")[:300],
            "stars": repo.get("stargazers_count"),
            "language": repo.get("language"),
        })
    return {
        "success": True,
        "query": q,
        "results": results,
    }

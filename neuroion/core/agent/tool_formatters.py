"""
Tool formatting for agent prompts and turn trace.

Builds tool lists for the agent loop prompt and summarizes tool results
for the observation log (TurnTrace).
"""
from typing import Any, Dict, List, Optional

# Max chars for web search result summary in trace
_WEB_SEARCH_SUMMARY_MAX = 2800


def tool_category(name: str) -> str:
    """Return category label for grouping tools in the plan prompt."""
    if not name:
        return "Other"
    if name.startswith("codebase."):
        return "Codebase"
    if name.startswith("cron."):
        return "Reminders/Scheduling"
    if name.startswith("agenda."):
        return "Agenda"
    if name.startswith("web."):
        return "Web/Research"
    if name in ("get_dashboard_link",):
        return "Dashboard"
    if name in ("generate_week_menu", "create_grocery_list", "summarize_family_preferences"):
        return "Meals/Preferences"
    return "Other"


def format_tool_params(parameters: Any) -> str:
    """Format JSON schema parameters as compact 'name, req, opt?' for agent context."""
    if not parameters or not isinstance(parameters, dict):
        return ""
    props = parameters.get("properties") or {}
    required = set(parameters.get("required") or [])
    if not props:
        return ""
    parts = [f"{key}?" if key not in required else key for key in props]
    return ", ".join(parts)


def tools_list_text_for_agent(
    tool_router: Any,
    allowed_tools: Optional[set] = None,
) -> str:
    """
    Build 'name(params): description' lines for agent loop prompt, grouped by category.
    If allowed_tools is set, only include those tools.
    """
    tools = tool_router.get_all_tools_for_llm()
    by_category: Dict[str, List[str]] = {}
    for t in tools:
        fn = t.get("function") or t
        name = fn.get("name") or t.get("name") or ""
        if not name:
            continue
        if allowed_tools is not None and name not in allowed_tools:
            continue
        desc = (fn.get("description") or t.get("description") or "")[:120]
        params_str = format_tool_params(fn.get("parameters"))
        line = f"- {name}({params_str}): {desc}" if params_str else f"- {name}: {desc}"
        cat = tool_category(name)
        by_category.setdefault(cat, []).append(line)
    order = ("Codebase", "Web/Research", "Reminders/Scheduling", "Agenda", "Dashboard", "Meals/Preferences", "Other")
    sections = []
    for cat in order:
        if cat in by_category and by_category[cat]:
            sections.append(f"{cat}:\n" + "\n".join(by_category[cat]))
    for cat, lines in by_category.items():
        if cat not in order:
            sections.append(f"{cat}:\n" + "\n".join(lines))
    return "\n\n".join(sections) if sections else "No tools."


def result_summary_for_trace(tool_name: str, result: Any) -> str:
    """Summary of tool result for turn trace. For web.search, include titles/URLs."""
    if not isinstance(result, dict):
        return str(result)[:200] if result else "ok"
    if result.get("success") is False:
        return f"error: {result.get('error', 'unknown')}"[:150]

    # Web search: pass through enough for final LLM
    if tool_name == "web.search" and "results" in result and isinstance(result["results"], list):
        return _format_search_results(result, "query", "title", "url", "snippet", 10)
    if tool_name == "web.shopping_search" and "results" in result and isinstance(result["results"], list):
        return _format_search_results(result, "query", "title", "url", "snippet", 5)
    if tool_name == "github.search" and "results" in result and isinstance(result["results"], list):
        lines = []
        for i, r in enumerate(result["results"][:5]):
            if not isinstance(r, dict):
                continue
            name = (r.get("name") or "").strip()
            url = (r.get("url") or "").strip()
            desc = (r.get("description") or "").strip()[:120]
            if name or url:
                lines.append(f"{i + 1}) {name} | {url}" if url else f"{i + 1}) {name}")
            if desc:
                lines.append(f"   {desc}")
        return "\n".join(lines)[:_WEB_SEARCH_SUMMARY_MAX] if lines else f"{len(result['results'])} repos"

    # Common shapes
    if "content" in result and isinstance(result.get("content"), str):
        preview = result["content"][:100].replace("\n", " ")
        return f"{len(result['content'])} chars" if len(result["content"]) > 100 else preview
    if "path" in result and "entries" in result:
        return f"{len(result['entries'])} entries"
    if "matches" in result:
        return f"{len(result['matches'])} matches"
    if "results" in result and isinstance(result["results"], list):
        return f"{len(result['results'])} results"
    if "menu" in result:
        return "menu generated"
    if "list" in result:
        return "list created"
    if "message" in result:
        return str(result["message"])[:80]
    return "ok"


def _format_search_results(
    result: Dict[str, Any],
    query_key: str,
    title_key: str,
    url_key: str,
    snippet_key: str,
    max_items: int,
) -> str:
    """Shared logic for web.search and web.shopping_search."""
    query = result.get(query_key) or ""
    lines = [f"Query: {query}"] if query else []
    for i, r in enumerate(result.get("results", [])[:max_items]):
        if not isinstance(r, dict):
            continue
        title = (r.get(title_key) or r.get("name") or "").strip()[:120]
        url = (r.get(url_key) or r.get("href") or r.get("link") or "").strip()
        snippet = (r.get(snippet_key) or r.get("body") or "").strip()[:150]
        if title or url:
            lines.append(f"{i + 1}) {title} | {url}" if url else f"{i + 1}) {title}")
        if snippet and len("\n".join(lines)) < _WEB_SEARCH_SUMMARY_MAX - 180:
            lines.append(f"   {snippet}")
        if len("\n".join(lines)) >= _WEB_SEARCH_SUMMARY_MAX:
            break
    if lines:
        return "\n".join(lines)[:_WEB_SEARCH_SUMMARY_MAX]
    return f"{len(result.get('results', []))} results"

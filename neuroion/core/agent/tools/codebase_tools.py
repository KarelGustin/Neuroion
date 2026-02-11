"""
Read-only codebase tools for the agent.

Allows the AI to read files, list directories, and search the codebase.
No write operations; path validation keeps access within the codebase root.
Max file size ~70k tokens (~280k bytes) so context stays within local model limits.
"""
import fnmatch
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from neuroion.core.agent.tool_registry import register_tool
from neuroion.core.config_store import get_neuroion_core_config

logger = logging.getLogger(__name__)

# ~70k tokens at ~4 chars/token so memory/chat context still fits in local model
MAX_FILE_BYTES = 280_000

# Limits for search and list to avoid token explosion
MAX_SEARCH_RESULTS = 100
MAX_LIST_RECURSIVE_DEPTH = 5
MAX_LIST_ITEMS = 500


def get_codebase_root(db: Optional[Session]) -> Path:
    """
    Return the codebase root path.
    Primary: workspace from neuroion_core config; fallback: repo root from this file.
    """
    if db is not None:
        core = get_neuroion_core_config(db)
        if core and isinstance(core.get("workspace"), str):
            p = Path(core["workspace"]).expanduser().resolve()
            if p.is_dir():
                return p
    # Fallback: repo root (this file is neuroion/core/agent/tools/codebase_tools.py)
    this_file = Path(__file__).resolve()
    return this_file.parent.parent.parent.parent


def resolve_relative_path(relative_path: str, root: Path) -> Optional[Path]:
    """
    Resolve a relative path against root and ensure it stays under root.
    Returns None if the path escapes the root (e.g. via ..).
    """
    if not root.is_dir():
        return None
    clean = relative_path.strip().lstrip("/")
    if not clean:
        return root
    try:
        resolved = (root / clean).resolve()
        resolved.relative_to(root)
        return resolved
    except (ValueError, OSError):
        return None


def _resolve_and_check_under_root(
    db: Session,
    household_id: int,
    relative_path: str,
    must_be_file: bool = False,
    must_be_dir: bool = False,
) -> Dict[str, Any]:
    """Shared helper: get root, resolve path, return error dict or None if ok."""
    root = get_codebase_root(db)
    resolved = resolve_relative_path(relative_path, root)
    if resolved is None:
        return {"success": False, "error": "Path is outside codebase root or invalid"}
    if must_be_file and not resolved.is_file():
        return {"success": False, "error": "Not a file"}
    if must_be_dir and not resolved.is_dir():
        return {"success": False, "error": "Not a directory"}
    return {"root": root, "resolved": resolved}


@register_tool(
    name="codebase.read_file",
    description=(
        "Read the contents of a single file in the codebase. "
        "Use for analyzing code, finding bugs, or suggesting improvements. "
        "Maximum ~70k tokens per file so model context and memory remain available. "
        "Path is relative to the codebase root (e.g. 'neuroion/core/agent/agent.py')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file from the codebase root",
            },
            "max_lines": {
                "type": "integer",
                "description": "Optional maximum number of lines to return (within token limit)",
            },
            "offset": {
                "type": "integer",
                "description": "Optional line offset (0-based) to start reading from",
            },
        },
        "required": ["path"],
    },
)
def codebase_read_file(
    db: Session,
    household_id: int,
    path: str,
    max_lines: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Read file contents. Enforces MAX_FILE_BYTES (~70k tokens).
    Returns truncated content and truncated=True if the file was cut.
    """
    out = _resolve_and_check_under_root(db, household_id, path, must_be_file=True)
    if "success" in out and out["success"] is False:
        return out
    resolved = out["resolved"]

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            if offset is not None and offset > 0:
                for _ in range(offset):
                    if f.readline() == "":
                        return {
                            "path": path,
                            "content": "",
                            "truncated": False,
                            "message": "Offset beyond file length",
                        }
            lines: List[str] = []
            total_bytes = 0
            for line in f:
                if max_lines is not None and len(lines) >= max_lines:
                    break
                line_bytes = line.encode("utf-8")
                remaining = MAX_FILE_BYTES - total_bytes
                if len(line_bytes) > remaining:
                    lines.append(line_bytes[:remaining].decode("utf-8", errors="replace"))
                    total_bytes = MAX_FILE_BYTES
                    break
                lines.append(line)
                total_bytes += len(line_bytes)
            content = "".join(lines)
            truncated = total_bytes >= MAX_FILE_BYTES or (max_lines is not None and len(lines) >= max_lines)
            return {
                "path": path,
                "content": content,
                "truncated": truncated,
                "bytes_returned": total_bytes,
                "message": "File truncated to fit context" if truncated else None,
            }
    except OSError as e:
        logger.warning("codebase.read_file failed for %s: %s", path, e)
        return {"success": False, "error": str(e)}


@register_tool(
    name="codebase.list_directory",
    description=(
        "List files and directories in a directory in the codebase. "
        "Path is relative to the codebase root; use empty string for root. "
        "Optional recursive listing with depth limit to avoid huge output."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the directory (empty string = codebase root)",
            },
            "recursive": {
                "type": "boolean",
                "description": "If true, list recursively with depth limit",
                "default": False,
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum depth when recursive (default 2)",
                "default": 2,
            },
        },
        "required": ["path"],
    },
)
def codebase_list_directory(
    db: Session,
    household_id: int,
    path: str = "",
    recursive: bool = False,
    max_depth: int = 2,
) -> Dict[str, Any]:
    """List directory contents; optionally recursive with depth and item limits."""
    out = _resolve_and_check_under_root(db, household_id, path, must_be_dir=True)
    if "success" in out and out["success"] is False:
        return out
    resolved = out["resolved"]
    root = out["root"]

    depth_limit = min(max(0, max_depth), MAX_LIST_RECURSIVE_DEPTH)
    items: List[Dict[str, Any]] = []
    count = 0

    def walk(current: Path, depth: int) -> None:
        nonlocal count
        if count >= MAX_LIST_ITEMS:
            return
        try:
            for p in sorted(current.iterdir()):
                if count >= MAX_LIST_ITEMS:
                    return
                try:
                    rel = p.relative_to(root)
                except ValueError:
                    continue
                entry: Dict[str, Any] = {
                    "path": str(rel),
                    "name": p.name,
                    "is_dir": p.is_dir(),
                }
                items.append(entry)
                count += 1
                if recursive and p.is_dir() and depth < depth_limit:
                    walk(p, depth + 1)
        except OSError:
            pass

    try:
        if recursive:
            walk(resolved, 0)
        else:
            for p in sorted(resolved.iterdir()):
                if count >= MAX_LIST_ITEMS:
                    break
                try:
                    rel = p.relative_to(root)
                except ValueError:
                    continue
                items.append({
                    "path": str(rel),
                    "name": p.name,
                    "is_dir": p.is_dir(),
                })
                count += 1
        return {
            "path": path or ".",
            "entries": items,
            "truncated": count >= MAX_LIST_ITEMS,
        }
    except OSError as e:
        logger.warning("codebase.list_directory failed for %s: %s", path, e)
        return {"success": False, "error": str(e)}


@register_tool(
    name="codebase.search",
    description=(
        "Search for text in the codebase (content or filenames). "
        "Use to find usages, definitions, or patterns. "
        "Results are limited to avoid overflowing model context."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text to search for (plain string, case-sensitive by default)",
            },
            "path": {
                "type": "string",
                "description": "Optional subdirectory to search in (relative to codebase root)",
                "default": "",
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional glob for file names (e.g. '*.py')",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matches to return",
                "default": 50,
            },
        },
        "required": ["query"],
    },
)
def codebase_search(
    db: Session,
    household_id: int,
    query: str,
    path: str = "",
    file_pattern: Optional[str] = None,
    max_results: int = 50,
) -> Dict[str, Any]:
    """Search for query in file contents under path; optional file_pattern glob."""
    if not query.strip():
        return {"success": False, "error": "query is required and must be non-empty"}
    root = get_codebase_root(db)
    search_root = root
    if path.strip():
        resolved = resolve_relative_path(path.strip(), root)
        if resolved is None or not resolved.is_dir():
            return {"success": False, "error": "path is outside codebase or not a directory"}
        search_root = resolved

    results: List[Dict[str, Any]] = []
    limit = min(max(1, max_results), MAX_SEARCH_RESULTS)

    try:
        for p in search_root.rglob("*"):
            if len(results) >= limit:
                break
            if p.is_dir():
                continue
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue
            if file_pattern and not fnmatch.fnmatch(p.name, file_pattern):
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f):
                        if query in line:
                            results.append({
                                "file": str(rel),
                                "line_number": i + 1,
                                "line": line.rstrip(),
                            })
                            if len(results) >= limit:
                                break
            except OSError:
                continue
        return {
            "query": query,
            "path": path or ".",
            "matches": results,
            "truncated": len(results) >= limit,
        }
    except OSError as e:
        logger.warning("codebase.search failed: %s", e)
        return {"success": False, "error": str(e)}

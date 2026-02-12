"""
Codebase skill: browse and search the project directory (~/Neuroion by default).

Lets the AI list folders/files, read file contents, and search the codebase
so users can ask questions about the actual code. Read-only; no writes.
"""
import fnmatch
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from neuroion.core.agent.tool_registry import register_tool
from neuroion.core.config_store import get_neuroion_core_config

logger = logging.getLogger(__name__)

# Default codebase root when not configured (user's Neuroion project)
DEFAULT_CODEBASE_ROOT = Path.home() / "Neuroion"

# ~70k tokens at ~4 chars/token so context stays within local model limits
MAX_FILE_BYTES = 280_000
MAX_SEARCH_RESULTS = 100
MAX_LIST_RECURSIVE_DEPTH = 5
MAX_LIST_ITEMS = 500


def get_codebase_root(db: Optional[Session]) -> Path:
    """
    Codebase root for browsing. Order: config workspace → ~/Neuroion → repo root.
    """
    if db is not None:
        core = get_neuroion_core_config(db)
        if core and isinstance(core.get("workspace"), str):
            p = Path(core["workspace"]).expanduser().resolve()
            if p.is_dir():
                return p
    if DEFAULT_CODEBASE_ROOT.is_dir():
        return DEFAULT_CODEBASE_ROOT
    # Fallback: repo root (this file is neuroion/core/skills/codebase.py)
    return Path(__file__).resolve().parent.parent.parent.parent


def _resolve_path(relative_path: str, root: Path) -> Optional[Path]:
    """Resolve path under root; return None if it escapes root."""
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


def _resolve_and_check(
    db: Session,
    household_id: int,
    relative_path: str,
    must_be_file: bool = False,
    must_be_dir: bool = False,
) -> Dict[str, Any]:
    """Resolve path under codebase root; return error dict or {root, resolved}."""
    root = get_codebase_root(db)
    resolved = _resolve_path(relative_path, root)
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
        "Read the contents of a file in the codebase (default root ~/Neuroion). "
        "Use to analyze code, find bugs, or answer questions about the codebase. "
        "Path is relative to the codebase root (e.g. 'neuroion/core/agent/agent.py'). "
        "Files are truncated to fit model context."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file from the codebase root",
            },
            "file_path": {
                "type": "string",
                "description": "Alias for path (relative path from codebase root)",
            },
            "max_lines": {
                "type": "integer",
                "description": "Optional maximum number of lines to return",
            },
            "offset": {
                "type": "integer",
                "description": "Optional line offset (0-based) to start reading from",
            },
        },
        "required": [],
    },
)
def codebase_read_file(
    db: Session,
    household_id: int,
    path: Optional[str] = None,
    file_path: Optional[str] = None,
    max_lines: Optional[int] = None,
    offset: Optional[int] = None,
) -> Dict[str, Any]:
    """Read file contents; enforces size limit for model context."""
    resolved_path = path or file_path
    if not resolved_path:
        return {"success": False, "error": "path or file_path is required"}
    out = _resolve_and_check(db, household_id, resolved_path, must_be_file=True)
    if "success" in out and out.get("success") is False:
        return out
    resolved = out["resolved"]

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            if offset is not None and offset > 0:
                for _ in range(offset):
                    if f.readline() == "":
                        return {
                            "path": resolved_path,
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
            truncated = total_bytes >= MAX_FILE_BYTES or (
                max_lines is not None and len(lines) >= max_lines
            )
            return {
                "path": resolved_path,
                "content": content,
                "truncated": truncated,
                "bytes_returned": total_bytes,
                "message": "File truncated to fit context" if truncated else None,
            }
    except OSError as e:
        logger.warning("codebase.read_file failed for %s: %s", resolved_path, e)
        return {"success": False, "error": str(e)}


@register_tool(
    name="codebase.list_directory",
    description=(
        "List files and folders in a directory in the codebase (default root ~/Neuroion). "
        "Use empty path for the root. Use to explore the project structure before reading files."
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
    out = _resolve_and_check(db, household_id, path, must_be_dir=True)
    if "success" in out and out.get("success") is False:
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
                items.append({
                    "path": str(rel),
                    "name": p.name,
                    "is_dir": p.is_dir(),
                })
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
            "root": str(root),
            "entries": items,
            "truncated": count >= MAX_LIST_ITEMS,
        }
    except OSError as e:
        logger.warning("codebase.list_directory failed for %s: %s", path, e)
        return {"success": False, "error": str(e)}


@register_tool(
    name="codebase.search",
    description=(
        "Search for text in the codebase (default root ~/Neuroion). "
        "Use to find usages, definitions, or patterns. Use when the user asks about where something is or how it works."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text to search for in file contents",
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
        resolved = _resolve_path(path.strip(), root)
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
            "root": str(root),
            "matches": results,
            "truncated": len(results) >= limit,
        }
    except OSError as e:
        logger.warning("codebase.search failed: %s", e)
        return {"success": False, "error": str(e)}

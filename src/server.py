"""MCP Server for local LanceDB + Kuzu memory."""

import json
from typing import Optional

from fastmcp import FastMCP

from config import DEFAULT_DECAY_DAYS, DEFAULT_TOP_K, ensure_dirs
from memory_service import MemoryService

mcp = FastMCP("local-memory")
service: Optional[MemoryService] = None


def get_service() -> MemoryService:
    """Lazy initialize memory service."""
    global service
    if service is None:
        ensure_dirs()
        service = MemoryService()
    return service


@mcp.tool()
def add_memory(
    content: str,
    memory_type: str = "short_term",
    source: str = "unknown",
    topic_tags: Optional[str] = None,
) -> str:
    """Add a new memory. Use topic_tags as comma-separated topics."""
    tags = [t.strip() for t in (topic_tags or "").split(",") if t.strip()]
    result = get_service().add_memory(
        content=content,
        memory_type=memory_type,
        source=source,
        topic_tags=tags,
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def search_memories(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    memory_type: Optional[str] = None,
) -> str:
    """Search memories by semantic similarity."""
    results = get_service().search_memories(query, top_k, memory_type)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def get_memory_context(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """Get combined vector + graph memory context for a query."""
    context = get_service().get_memory_context(query, top_k)
    return json.dumps(context, ensure_ascii=False)


@mcp.tool()
def list_memories(limit: int = 20, memory_type: Optional[str] = None) -> str:
    """List recent memories."""
    results = get_service().list_memories(limit, memory_type)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """Delete a memory by id."""
    success = get_service().delete_memory(memory_id)
    return json.dumps({"success": success, "id": memory_id}, ensure_ascii=False)


@mcp.tool()
def update_memory(
    memory_id: str,
    content: Optional[str] = None,
    memory_type: Optional[str] = None,
    topic_tags: Optional[str] = None,
) -> str:
    """Update a memory. Pass only fields to change."""
    tags = None
    if topic_tags is not None:
        tags = [t.strip() for t in topic_tags.split(",") if t.strip()]
        if not tags:
            tags = None
    success = get_service().update_memory(memory_id, content, memory_type, tags)
    return json.dumps({"success": success, "id": memory_id}, ensure_ascii=False)


@mcp.tool()
def promote_memory(memory_id: str) -> str:
    """Promote a short-term memory to long-term."""
    success = get_service().promote_memory(memory_id)
    return json.dumps({"success": success, "id": memory_id}, ensure_ascii=False)


@mcp.tool()
def decay_memories(days: int = DEFAULT_DECAY_DAYS) -> str:
    """Delete short-term memories older than N days."""
    count = get_service().decay_memories(days)
    return json.dumps({"deleted": count}, ensure_ascii=False)


@mcp.tool()
def consolidate_memories() -> str:
    """Merge highly similar short-term memories into long-term summaries."""
    result = get_service().consolidate_memories()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def search_graph(
    topic: Optional[str] = None,
    project: Optional[str] = None,
    tool: Optional[str] = None,
    memory_id: Optional[str] = None,
    depth: int = 1,
) -> str:
    """Search memories via graph relationships."""
    results = get_service().search_graph(topic, project, tool, memory_id, depth)
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def backup_memories() -> str:
    """Export all memories to a JSONL backup file."""
    result = get_service().backup()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def memory_stats() -> str:
    """Return memory statistics."""
    stats = get_service().count()
    return json.dumps(stats, ensure_ascii=False)


if __name__ == "__main__":
    ensure_dirs()
    mcp.run(transport="stdio")

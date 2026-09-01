"""High-level memory service combining vector store and graph store."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import DEFAULT_DECAY_DAYS, DEFAULT_TOP_K, SIMILARITY_THRESHOLD
from graph_store import GraphMemoryStore
from lance_store import LanceMemoryStore


class MemoryService:
    """Unified memory service with vector + graph capabilities."""

    def __init__(self) -> None:
        self.vector_store = LanceMemoryStore()
        self.graph_store = GraphMemoryStore()

    def add_memory(
        self,
        content: str,
        memory_type: str = "short_term",
        source: str = "unknown",
        topic_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a memory to both vector and graph stores."""
        memory_id = self.vector_store.add_memory(
            content=content,
            memory_type=memory_type,
            source=source,
            topic_tags=topic_tags,
        )

        now = int(datetime.now(timezone.utc).timestamp())
        self.graph_store.add_memory_node(memory_id, memory_type, now)

        entities = self.graph_store.extract_entities(content, topic_tags)
        for topic in entities["topics"]:
            self.graph_store.link_topic(memory_id, topic)
        for project in entities["projects"]:
            self.graph_store.link_project(memory_id, project)
        for tool in entities["tools"]:
            self.graph_store.link_tool(memory_id, tool)

        # Link to most recent memory for temporal ordering
        recent = self.vector_store.list_memories(limit=2, memory_type=memory_type)
        for item in recent:
            if item["id"] != memory_id:
                self.graph_store.link_before(item["id"], memory_id)
                break

        return {
            "id": memory_id,
            "content": content,
            "memory_type": memory_type,
            "source": source,
            "topic_tags": entities["topics"],
            "projects": entities["projects"],
            "tools": entities["tools"],
        }

    def search_memories(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Vector search memories."""
        return self.vector_store.search_memories(query, top_k, memory_type)

    def get_memory_context(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> Dict[str, Any]:
        """Combine vector search with graph expansion."""
        vector_results = self.vector_store.search_memories(query, top_k=top_k)
        vector_ids = {r["id"] for r in vector_results}

        # Expand via graph: related memories
        graph_results = []
        for r in vector_results:
            related = self.graph_store.get_related_memories(r["id"], depth=1)
            for rel in related:
                if rel["id"] not in vector_ids:
                    graph_results.append(rel)
                    vector_ids.add(rel["id"])

        # Fetch full content for graph-only ids
        graph_memories = []
        for item in graph_results:
            full = self.vector_store.get_memory(item["id"])
            if full:
                graph_memories.append(full)

        # Deduplicate combined results by id
        combined = []
        seen_ids = set()
        for item in vector_results + graph_memories:
            if item["id"] not in seen_ids:
                combined.append(item)
                seen_ids.add(item["id"])

        return {
            "vector_results": vector_results,
            "graph_results": graph_memories,
            "combined": combined,
        }

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory from both stores."""
        self.graph_store.delete_memory(memory_id)
        return self.vector_store.delete_memory(memory_id)

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        topic_tags: Optional[List[str]] = None,
    ) -> bool:
        """Update a memory. Rebuilds graph relationships if content changed."""
        success = self.vector_store.update_memory(memory_id, content, memory_type, topic_tags)
        if not success:
            return False

        if content is not None or topic_tags is not None:
            # Rebuild graph entities
            self.graph_store.delete_memory(memory_id)
            full = self.vector_store.get_memory(memory_id)
            self.graph_store.add_memory_node(
                memory_id, full["memory_type"], full["created_at"]
            )
            entities = self.graph_store.extract_entities(content or full["content"], topic_tags)
            for topic in entities["topics"]:
                self.graph_store.link_topic(memory_id, topic)
            for project in entities["projects"]:
                self.graph_store.link_project(memory_id, project)
            for tool in entities["tools"]:
                self.graph_store.link_tool(memory_id, tool)

        return True

    def promote_memory(self, memory_id: str) -> bool:
        """Promote a short-term memory to long-term."""
        return self.vector_store.update_memory(memory_id, memory_type="long_term")

    def decay_memories(self, days: int = DEFAULT_DECAY_DAYS) -> int:
        """Remove old short-term memories."""
        # Find ids first so we can delete from graph too
        cutoff = int(datetime.now(timezone.utc).timestamp()) - days * 86400
        candidates = self.vector_store.table.search().where(
            f"memory_type = 'short_term' AND created_at < {cutoff}"
        ).to_list()

        count = 0
        for item in candidates:
            if self.delete_memory(item["id"]):
                count += 1
        return count

    def consolidate_memories(self, threshold: float = SIMILARITY_THRESHOLD) -> Dict[str, Any]:
        """Merge highly similar short-term memories into a single long-term summary."""
        short_term = self.vector_store.list_memories(limit=100, memory_type="short_term")
        if len(short_term) < 2:
            return {"merged": 0, "summary": None}

        merged = 0
        seen = set()
        for item in short_term:
            if item["id"] in seen:
                continue
            similar = self.vector_store.find_similar(item["content"], threshold=threshold)
            group_ids = [s["id"] for s in similar if s["id"] != item["id"]]
            if not group_ids:
                continue

            group_ids.append(item["id"])
            seen.update(group_ids)

            contents = [s["content"] for s in similar]
            contents.append(item["content"])
            summary = "；".join(contents)

            # Create long-term consolidated memory
            self.add_memory(
                content=f"[合并记忆] {summary}",
                memory_type="long_term",
                source="consolidation",
                topic_tags=item["topic_tags"].split(",") if item["topic_tags"] else [],
            )

            # Delete old short-term memories
            for mid in group_ids:
                self.delete_memory(mid)
            merged += 1

        return {"merged": merged}

    def list_memories(
        self,
        limit: int = 20,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List memories."""
        return self.vector_store.list_memories(limit, memory_type)

    def search_graph(
        self,
        topic: Optional[str] = None,
        project: Optional[str] = None,
        tool: Optional[str] = None,
        memory_id: Optional[str] = None,
        depth: int = 1,
    ) -> List[Dict[str, Any]]:
        """Search memories via graph relationships."""
        if topic:
            rows = self.graph_store.search_by_topic(topic, depth)
        elif memory_id:
            rows = self.graph_store.get_related_memories(memory_id, depth)
        else:
            return []

        results = []
        for row in rows:
            full = self.vector_store.get_memory(row["id"])
            if full:
                results.append(full)
        return results

    def backup(self) -> Dict[str, Any]:
        """Export all memories to a JSONL backup."""
        import json

        from config import BACKUP_DIR, ensure_dirs

        ensure_dirs()
        now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"memories-{now}.jsonl"

        rows = self.vector_store.export_all()
        for row in rows:
            row["topics"] = self.graph_store.get_memory_topics(row["id"])

        with open(backup_file, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        return {"file": str(backup_file), "count": len(rows)}

    def count(self) -> Dict[str, int]:
        """Return memory counts."""
        return {
            "total": self.vector_store.count(),
        }

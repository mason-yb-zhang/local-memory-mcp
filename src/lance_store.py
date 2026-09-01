"""LanceDB vector store for memories."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import lancedb
import pyarrow as pa
from lancedb.pydantic import LanceModel, Vector

from config import (
    DEFAULT_TOP_K,
    EMBEDDING_DIMENSION,
    LANCEDB_DIR,
    MEMORY_TABLE,
)
from embedding import embed_text, embed_texts


class MemoryModel(LanceModel):
    """Pydantic schema for the memories table."""

    id: str
    content: str
    memory_type: str  # short_term | long_term
    source: str
    topic_tags: str
    created_at: int
    vector: Vector(EMBEDDING_DIMENSION)


class LanceMemoryStore:
    """Vector store backed by LanceDB."""

    def __init__(self, db_path: str = str(LANCEDB_DIR)) -> None:
        self.db = lancedb.connect(db_path)
        self.table: Optional[lancedb.table.Table] = None
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Open existing table or create a new one."""
        if MEMORY_TABLE in self.db.table_names():
            self.table = self.db.open_table(MEMORY_TABLE)
            return

        self.table = self.db.create_table(
            MEMORY_TABLE,
            schema=MemoryModel,
            mode="create",
        )
        # Create vector index for cosine similarity
        try:
            self.table.create_index(
                index_type="IVF_PQ",
                metric="cosine",
                num_partitions=16,
                num_sub_vectors=8,
                replace=True,
            )
        except Exception:
            # Index creation may fail on empty table; retry after first insert
            pass

    def add_memory(
        self,
        content: str,
        memory_type: str = "short_term",
        source: str = "unknown",
        topic_tags: Optional[List[str]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """Add a memory and return its id."""
        memory_id = memory_id or uuid.uuid4().hex
        vector = embed_text(content)
        now = int(datetime.now(timezone.utc).timestamp())

        self.table.add(
            [
                {
                    "id": memory_id,
                    "content": content,
                    "memory_type": memory_type,
                    "source": source,
                    "topic_tags": ",".join(topic_tags or []),
                    "created_at": now,
                    "vector": vector,
                }
            ]
        )
        return memory_id

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a single memory by id."""
        result = self.table.search().where(f"id = '{memory_id}'").limit(1).to_list()
        return result[0] if result else None

    def search_memories(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Vector search memories by query text."""
        query_vector = embed_text(query)
        search = self.table.search(query_vector, vector_column_name="vector").metric("cosine")

        if memory_type:
            search = search.where(f"memory_type = '{memory_type}'", prefilter=True)

        return search.limit(top_k).to_list()

    def list_memories(
        self,
        limit: int = 20,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List recent memories."""
        query = self.table.search().limit(limit)
        if memory_type:
            query = query.where(f"memory_type = '{memory_type}'")
        return query.to_list()

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by id. Returns True if deleted."""
        before = self.table.count_rows()
        self.table.delete(f"id = '{memory_id}'")
        after = self.table.count_rows()
        return after < before

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        topic_tags: Optional[List[str]] = None,
    ) -> bool:
        """Update memory fields. Re-embeds if content changed."""
        existing = self.get_memory(memory_id)
        if not existing:
            return False

        new_content = content if content is not None else existing["content"]
        new_type = memory_type if memory_type is not None else existing["memory_type"]
        new_tags = topic_tags if topic_tags is not None else existing["topic_tags"].split(",")

        vector = embed_text(new_content) if content else existing["vector"]

        self.delete_memory(memory_id)
        self.table.add(
            [
                {
                    "id": memory_id,
                    "content": new_content,
                    "memory_type": new_type,
                    "source": existing["source"],
                    "topic_tags": ",".join(new_tags),
                    "created_at": existing["created_at"],
                    "vector": vector,
                }
            ]
        )
        return True

    def find_similar(
        self,
        content: str,
        threshold: float = 0.92,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find memories semantically similar to given content."""
        query_vector = embed_text(content)
        results = (
            self.table.search(query_vector, vector_column_name="vector")
            .metric("cosine")
            .limit(top_k)
            .to_list()
        )
        # Cosine distance in LanceDB is 1 - cosine_similarity
        return [r for r in results if r.get("_distance", 1.0) < (1 - threshold)]

    def delete_old_short_term(self, days: int) -> int:
        """Delete short-term memories older than N days."""
        cutoff = int(datetime.now(timezone.utc).timestamp()) - days * 86400
        before = self.table.count_rows()
        self.table.delete(f"memory_type = 'short_term' AND created_at < {cutoff}")
        after = self.table.count_rows()
        return before - after

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all memories as plain dicts (without vectors for readability)."""
        rows = self.table.to_arrow().to_pylist()
        for row in rows:
            row.pop("vector", None)
        return rows

    def count(self) -> int:
        """Return total number of memories."""
        return self.table.count_rows()

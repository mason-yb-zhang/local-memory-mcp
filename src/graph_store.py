"""Kuzu graph store for memory relationships."""

import re
from datetime import datetime, timezone
from typing import List, Optional

import kuzu

from config import KUZU_DB


class GraphMemoryStore:
    """Graph store backed by Kuzu for memory relationships."""

    def __init__(self, db_path: str = str(KUZU_DB)) -> None:
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create node and relationship tables if they don't exist."""
        schema_statements = [
            "CREATE NODE TABLE IF NOT EXISTS Memory(id STRING, type STRING, created_at INT64, PRIMARY KEY(id))",
            "CREATE NODE TABLE IF NOT EXISTS Topic(name STRING, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Person(name STRING, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Project(name STRING, PRIMARY KEY(name))",
            "CREATE NODE TABLE IF NOT EXISTS Tool(name STRING, PRIMARY KEY(name))",
            "CREATE REL TABLE IF NOT EXISTS About(FROM Memory TO Topic)",
            "CREATE REL TABLE IF NOT EXISTS Involves(FROM Memory TO Person)",
            "CREATE REL TABLE IF NOT EXISTS InProject(FROM Memory TO Project)",
            "CREATE REL TABLE IF NOT EXISTS UsesTool(FROM Memory TO Tool)",
            "CREATE REL TABLE IF NOT EXISTS RelatedTo(FROM Memory TO Memory, relation STRING)",
            "CREATE REL TABLE IF NOT EXISTS Before(FROM Memory TO Memory)",
        ]
        for stmt in schema_statements:
            try:
                self.conn.execute(stmt)
            except Exception:
                # Table may already exist; ignore
                pass

    def _sanitize(self, value: str) -> str:
        """Escape single quotes for Cypher queries."""
        return value.replace("'", "\\'")

    def add_memory_node(
        self,
        memory_id: str,
        memory_type: str,
        created_at: int,
    ) -> None:
        """Create a Memory node."""
        self.conn.execute(
            f"MERGE (m:Memory {{id: '{self._sanitize(memory_id)}'}}) "
            f"SET m.type = '{self._sanitize(memory_type)}', m.created_at = {created_at}"
        )

    def link_topic(self, memory_id: str, topic: str) -> None:
        """Create a Memory -> Topic relationship."""
        topic = self._sanitize(topic)
        mid = self._sanitize(memory_id)
        self.conn.execute(
            f"MATCH (m:Memory {{id: '{mid}'}}) "
            f"MERGE (t:Topic {{name: '{topic}'}}) "
            f"CREATE (m)-[:About]->(t)"
        )

    def link_project(self, memory_id: str, project: str) -> None:
        """Create a Memory -> Project relationship."""
        project = self._sanitize(project)
        mid = self._sanitize(memory_id)
        self.conn.execute(
            f"MATCH (m:Memory {{id: '{mid}'}}) "
            f"MERGE (p:Project {{name: '{project}'}}) "
            f"CREATE (m)-[:InProject]->(p)"
        )

    def link_tool(self, memory_id: str, tool: str) -> None:
        """Create a Memory -> Tool relationship."""
        tool = self._sanitize(tool)
        mid = self._sanitize(memory_id)
        self.conn.execute(
            f"MATCH (m:Memory {{id: '{mid}'}}) "
            f"MERGE (t:Tool {{name: '{tool}'}}) "
            f"CREATE (m)-[:UsesTool]->(t)"
        )

    def link_related(
        self,
        from_id: str,
        to_id: str,
        relation: str = "related",
    ) -> None:
        """Create a relationship between two memories."""
        from_id = self._sanitize(from_id)
        to_id = self._sanitize(to_id)
        relation = self._sanitize(relation)
        self.conn.execute(
            f"MATCH (a:Memory {{id: '{from_id}'}}), (b:Memory {{id: '{to_id}'}}) "
            f"CREATE (a)-[:RelatedTo {{relation: '{relation}'}}]->(b)"
        )

    def link_before(self, earlier_id: str, later_id: str) -> None:
        """Create a temporal Before relationship."""
        earlier_id = self._sanitize(earlier_id)
        later_id = self._sanitize(later_id)
        self.conn.execute(
            f"MATCH (a:Memory {{id: '{earlier_id}'}}), (b:Memory {{id: '{later_id}'}}) "
            f"CREATE (a)-[:Before]->(b)"
        )

    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory node and all its relationships."""
        mid = self._sanitize(memory_id)
        # Kuzu does not support DETACH DELETE in older versions; delete relationships first
        self.conn.execute(f"MATCH (m:Memory {{id: '{mid}'}})-[r]->() DELETE r")
        self.conn.execute(f"MATCH (m:Memory {{id: '{mid}'}}) DELETE m")

    def _fetch_dicts(self, result) -> List[dict]:
        """Convert Kuzu query result rows into dicts."""
        columns = result.get_column_names()
        rows = []
        while result.has_next():
            values = result.get_next()
            rows.append(dict(zip(columns, values)))
        return rows

    def search_by_topic(self, topic: str, depth: int = 1) -> List[dict]:
        """Find memories related to a topic, optionally expanding by depth."""
        topic = self._sanitize(topic)
        query = (
            f"MATCH (m:Memory)-[:About]->(t:Topic {{name: '{topic}'}}) "
            f"RETURN m.id AS id, m.type AS type, m.created_at AS created_at"
        )
        result = self.conn.execute(query)
        return self._fetch_dicts(result)

    def get_related_memories(self, memory_id: str, depth: int = 1) -> List[dict]:
        """Find memories related to a given memory via graph hops."""
        mid = self._sanitize(memory_id)
        query = (
            f"MATCH (m:Memory {{id: '{mid}'}})-[:RelatedTo|Before*1..{depth}]-(n:Memory) "
            f"RETURN DISTINCT n.id AS id, n.type AS type, n.created_at AS created_at"
        )
        result = self.conn.execute(query)
        return self._fetch_dicts(result)

    def get_memory_topics(self, memory_id: str) -> List[str]:
        """Return all topics linked to a memory."""
        mid = self._sanitize(memory_id)
        query = (
            f"MATCH (m:Memory {{id: '{mid}'}})-[:About]->(t:Topic) "
            f"RETURN t.name AS name"
        )
        result = self.conn.execute(query)
        rows = []
        while result.has_next():
            values = result.get_next()
            rows.append(values[0])
        return rows

    def extract_entities(self, content: str, topic_tags: Optional[List[str]] = None) -> dict:
        """Naive entity extraction from content and tags."""
        entities = {
            "topics": list(topic_tags or []),
            "projects": [],
            "tools": [],
        }

        # Common Chinese/English tool names
        tool_patterns = [
            r"\b(VS Code|Cursor|PyCharm|IntelliJ|WebStorm|CLion)\b",
            r"\b(Git|GitHub|GitLab|Docker|Kubernetes|K8s)\b",
            r"\b(Node\.js|Python|TypeScript|JavaScript|Go|Rust|Java|C\+\+|C#)\b",
            r"\b(LanceDB|Kuzu|Postgres|MySQL|MongoDB|Redis|Elasticsearch)\b",
            r"\b(Kimi Code|workbuddy|Cursor|Copilot|Claude)\b",
        ]
        for pattern in tool_patterns:
            entities["tools"].extend(re.findall(pattern, content, flags=re.IGNORECASE))

        # Project names: quoted or capitalized phrases
        project_patterns = [
            r"项目[\s:：是]?['\"]?([^'\"，。；]{2,30})['\"]?",
            r"project[\s:]*['\"]?([^'\"，。；]{2,30})['\"]?",
        ]
        for pattern in project_patterns:
            entities["projects"].extend(re.findall(pattern, content, flags=re.IGNORECASE))

        # Deduplicate
        entities["tools"] = list(set(entities["tools"]))
        entities["projects"] = list(set(entities["projects"]))
        entities["topics"] = list(set(entities["topics"]))

        return entities

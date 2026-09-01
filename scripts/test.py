#!/usr/bin/env python3
"""Quick test for local-memory-mcp."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from memory_service import MemoryService


def main() -> int:
    print("Initializing memory service...")
    service = MemoryService()

    print("\n1. Adding short-term memory...")
    r1 = service.add_memory(
        content="用户喜欢用 TypeScript 写项目",
        memory_type="short_term",
        source="test",
        topic_tags=["TypeScript", "偏好"],
    )
    print(f"Added: {r1['id']}")

    print("\n2. Adding long-term memory...")
    r2 = service.add_memory(
        content="用户主力编辑器是 VS Code",
        memory_type="long_term",
        source="test",
        topic_tags=["VS Code", "工具"],
    )
    print(f"Added: {r2['id']}")

    print("\n3. Vector search...")
    results = service.search_memories("用户常用的编程语言", top_k=3)
    for r in results:
        print(f"  - {r['content']} (type={r['memory_type']})")

    print("\n4. Graph search by topic...")
    graph_results = service.search_graph(topic="TypeScript")
    for r in graph_results:
        print(f"  - {r['content']}")

    print("\n5. Combined context...")
    context = service.get_memory_context("用户开发环境", top_k=3)
    for r in context["combined"]:
        print(f"  - {r['content']}")

    print("\n6. Memory stats...")
    print(service.count())

    print("\n7. Backup...")
    backup = service.backup()
    print(f"Backup: {backup}")

    print("\n8. Delete one memory...")
    deleted = service.delete_memory(r1["id"])
    print(f"Deleted: {deleted}")

    print("\n9. Final stats...")
    print(service.count())

    print("\nAll tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

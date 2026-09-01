"""Configuration and paths for local-memory-mcp."""

import os
from pathlib import Path

HOME = Path.home()

DATA_DIR = Path(os.getenv("LOCAL_MEMORY_DATA_DIR", HOME / ".kimi-memory"))
LANCEDB_DIR = DATA_DIR / "lancedb"
KUZU_DB = DATA_DIR / "memory.kuzu"
MODEL_DIR = DATA_DIR / "models"
BACKUP_DIR = DATA_DIR / "backups"
CONFIG_FILE = DATA_DIR / "config.yaml"

EMBEDDING_MODEL = os.getenv("LOCAL_MEMORY_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_DIMENSION = int(os.getenv("LOCAL_MEMORY_EMBEDDING_DIMENSION", "512"))
EMBEDDING_INSTRUCTION = "为这个句子生成嵌入向量用于检索相关记忆："

# Search defaults
DEFAULT_TOP_K = int(os.getenv("LOCAL_MEMORY_DEFAULT_TOP_K", "5"))
DEFAULT_DECAY_DAYS = int(os.getenv("LOCAL_MEMORY_DEFAULT_DECAY_DAYS", "30"))
SIMILARITY_THRESHOLD = float(os.getenv("LOCAL_MEMORY_SIMILARITY_THRESHOLD", "0.92"))

# LanceDB table name
MEMORY_TABLE = "memories"


def ensure_dirs() -> None:
    """Create all data directories if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LANCEDB_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

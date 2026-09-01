#!/usr/bin/env python3
"""Install local-memory-mcp and register it with Kimi Code."""

import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = SKILL_DIR / "src"
CONFIG_DIR = Path.home() / ".kimi-code" / "config"
MCP_CONFIG = CONFIG_DIR / "mcp.json"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_venv() -> Path:
    """Create virtual environment if it doesn't exist."""
    venv_dir = SKILL_DIR / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    return venv_dir


def install_dependencies(venv_dir: Path) -> None:
    """Install Python dependencies."""
    python = venv_dir / "bin" / "python"
    if not python.exists():
        python = venv_dir / "Scripts" / "python.exe"

    print("Installing dependencies...")
    # Use python -m pip to avoid Windows pip.exe self-replacement issue
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-e", str(SKILL_DIR)])


def download_model(venv_dir: Path) -> None:
    """Pre-download embedding model to avoid first-run delay."""
    python = venv_dir / "bin" / "python"
    if not python.exists():
        python = venv_dir / "Scripts" / "python.exe"

    print("Pre-downloading embedding model...")
    script = (
        "from sentence_transformers import SentenceTransformer; "
        "from pathlib import Path; "
        "import sys; "
        "sys.path.insert(0, r'" + str(SRC_DIR) + "'); "
        "from config import MODEL_DIR, EMBEDDING_MODEL; "
        "SentenceTransformer(EMBEDDING_MODEL, cache_folder=str(MODEL_DIR))"
    )
    run([str(python), "-c", script])


def register_mcp(venv_dir: Path) -> None:
    """Register MCP server in Kimi Code config."""
    python = venv_dir / "bin" / "python"
    if not python.exists():
        python = venv_dir / "Scripts" / "python.exe"

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config: dict = {}
    if MCP_CONFIG.exists():
        with open(MCP_CONFIG, "r", encoding="utf-8") as f:
            config = json.load(f)

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["local-memory"] = {
        "command": str(python),
        "args": [str(SRC_DIR / "server.py")],
        "env": {
            "PYTHONPATH": str(SRC_DIR),
        },
        "disabled": False,
    }

    with open(MCP_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Registered local-memory in {MCP_CONFIG}")


def main() -> int:
    print("Installing local-memory-mcp...")
    venv_dir = ensure_venv()
    install_dependencies(venv_dir)
    download_model(venv_dir)
    register_mcp(venv_dir)
    print("\nDone. Please restart Kimi Code CLI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

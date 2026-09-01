#!/usr/bin/env python3
"""Backup local memory data to Baidu Netdisk sync folder or a target directory."""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import BACKUP_DIR, DATA_DIR  # noqa: E402


def get_baidu_sync_dir() -> Path | None:
    """Auto-detect common Baidu Netdisk sync directories."""
    home = Path.home()
    candidates = [
        home / "BaiduNetdisk",
        home / "百度网盘",
        home / "OneDrive" / "百度网盘",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def export_jsonl(backup_dir: Path) -> Path:
    """Export memories via the MCP service to JSONL."""
    from memory_service import MemoryService

    service = MemoryService()
    result = service.backup()
    return Path(result["file"])


def pack_data_dir(target_dir: Path) -> Path:
    """Pack the entire data directory into a tarball."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"kimi-memory-{now}"
    archive_path = target_dir / archive_name

    print(f"Packing {DATA_DIR} -> {archive_path}.tar.gz")
    shutil.make_archive(
        base_name=str(archive_path),
        format="gztar",
        root_dir=str(DATA_DIR),
    )
    return Path(f"{archive_path}.tar.gz")


def cleanup_old_backups(target_dir: Path, keep: int = 10) -> None:
    """Keep only the most recent N archives."""
    archives = sorted(target_dir.glob("kimi-memory-*.tar.gz"))
    for old in archives[:-keep]:
        print(f"Removing old backup: {old}")
        old.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup local memory data")
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target backup directory (default: Baidu Netdisk sync dir)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Number of full backups to keep",
    )
    parser.add_argument(
        "--jsonl-only",
        action="store_true",
        help="Only export JSONL, skip full archive",
    )
    args = parser.parse_args()

    target = Path(args.target) if args.target else get_baidu_sync_dir()
    if target is None:
        print("Could not find Baidu Netdisk sync dir. Use --target to specify one.")
        target = BACKUP_DIR
        print(f"Falling back to {target}")

    target.mkdir(parents=True, exist_ok=True)

    # Always export JSONL first
    jsonl_file = export_jsonl(target)
    print(f"Exported JSONL: {jsonl_file}")

    if not args.jsonl_only:
        archive = pack_data_dir(target)
        print(f"Created archive: {archive}")
        cleanup_old_backups(target, args.keep)

    return 0


if __name__ == "__main__":
    sys.exit(main())

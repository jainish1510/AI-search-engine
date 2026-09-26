"""Load sample documents into the index.

Usage: python -m app.seed [--reset] [path/to/documents.json]
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from . import db
from .services.indexer import index_document

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "sample_documents.json"
COLLECTIONS = ("documents", "postings", "terms", "vocab", "stats", "queries", "jobs")


async def seed(path: Path, reset: bool) -> int:
    database = await db.connect()
    try:
        if reset:
            for name in COLLECTIONS:
                await database[name].delete_many({})
        documents = json.loads(path.read_text(encoding="utf-8"))
        for data in documents:
            await index_document(database, data)
        return len(documents)
    finally:
        await db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--reset", action="store_true", help="clear the index before loading")
    args = parser.parse_args()
    count = asyncio.run(seed(args.path, args.reset))
    print(f"Indexed {count} documents from {args.path}")


if __name__ == "__main__":
    main()

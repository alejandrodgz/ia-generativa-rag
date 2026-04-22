#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from typing import cast


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rag_adm.index_metadata import read_index_metadata  # noqa: E402
from rag_adm.knowledge_base import KnowledgeBase  # noqa: E402
from rag_adm.settings import Settings, get_settings  # noqa: E402
from rag_adm.vector_store import build_or_load_vector_store, get_vector_index_status  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reindexa el vector store de forma controlada (full o incremental).",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="full: elimina y reconstruye; incremental: conserva indice existente y solo crea si falta.",
    )
    parser.add_argument(
        "--base-path",
        default=str(REPO_ROOT),
        help="Ruta raiz del repositorio (default: actual).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_path = Path(args.base_path).resolve()

    settings = get_settings()
    runtime_settings = cast(
        Settings,
        replace(
            settings,
            vector_rebuild_index=True,
            vector_rebuild_policy=args.mode,
        ),
    )

    knowledge_base = KnowledgeBase.load(base_path)
    build_or_load_vector_store(knowledge_base, runtime_settings, base_path)

    status = get_vector_index_status(runtime_settings, base_path)

    persist_path = Path(runtime_settings.vector_store_path)
    if not persist_path.is_absolute():
        persist_path = (base_path / runtime_settings.vector_store_path).resolve()
    index_metadata = read_index_metadata(persist_path)

    output = {
        "mode": args.mode,
        "status": status,
        "index_metadata": index_metadata,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if not status["vector_index_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

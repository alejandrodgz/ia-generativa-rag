from __future__ import annotations

import json
from pathlib import Path

from rag_adm.index_metadata import (
    build_sources_snapshot,
    read_index_metadata,
    validate_index_metadata,
    write_index_metadata,
)


def _create_min_source_tree(base_path: Path) -> None:
    data_dir = base_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "politicas_acceso.json").write_text("{}", encoding="utf-8")
    (data_dir / "catalogo_permisos.json").write_text("[]", encoding="utf-8")
    (data_dir / "historico_configuraciones.json").write_text("[]", encoding="utf-8")


def test_snapshot_is_deterministic(tmp_path: Path) -> None:
    _create_min_source_tree(tmp_path)

    first = build_sources_snapshot(tmp_path, docs_path=None)
    second = build_sources_snapshot(tmp_path, docs_path=None)

    assert first["combined_sha256"] == second["combined_sha256"]
    assert first["source_count"] == 3


def test_validate_detects_source_changes(tmp_path: Path) -> None:
    _create_min_source_tree(tmp_path)
    persist_dir = tmp_path / "vector_store"

    write_index_metadata(
        persist_dir,
        collection_name="adm_test",
        embedding_model="test-model",
        collection_size=10,
        base_path=tmp_path,
        docs_path=None,
        rebuild_mode="full",
    )

    valid_status = validate_index_metadata(
        persist_dir,
        base_path=tmp_path,
        docs_path=None,
    )
    assert valid_status["is_valid"] is True

    # Mutar fuente para invalidar firma
    politicas_path = tmp_path / "data" / "politicas_acceso.json"
    politicas_path.write_text(json.dumps({"changed": True}), encoding="utf-8")

    invalid_status = validate_index_metadata(
        persist_dir,
        base_path=tmp_path,
        docs_path=None,
    )
    assert invalid_status["is_valid"] is False
    assert invalid_status["reason"] == "source_snapshot_changed"


def test_read_index_metadata_returns_none_if_missing(tmp_path: Path) -> None:
    assert read_index_metadata(tmp_path) is None

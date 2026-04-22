from __future__ import annotations

from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
from typing import Any

from .enrichment import SYNTHETIC_CASES_FILE, USER_DOCS_DIR


INDEX_METADATA_FILENAME = "index_metadata.json"


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def _collect_source_files(base_path: Path, docs_path: str | None) -> list[Path]:
    data_dir = base_path / "data"
    files: list[Path] = [
        data_dir / "politicas_acceso.json",
        data_dir / "catalogo_permisos.json",
        data_dir / "historico_configuraciones.json",
        base_path / SYNTHETIC_CASES_FILE,
    ]

    user_docs_dir = base_path / USER_DOCS_DIR
    if user_docs_dir.exists() and user_docs_dir.is_dir():
        files.extend(sorted(user_docs_dir.glob("*.txt")))

    if docs_path:
        docs_dir = Path(docs_path)
        if not docs_dir.is_absolute():
            docs_dir = (base_path / docs_path).resolve()
        if docs_dir.exists() and docs_dir.is_dir():
            files.extend(sorted(docs_dir.glob("**/*.pdf")))

    return [file for file in files if file.exists() and file.is_file()]


def build_sources_snapshot(base_path: Path, docs_path: str | None) -> dict[str, Any]:
    files = _collect_source_files(base_path, docs_path)

    entries: list[dict[str, Any]] = []
    for file in files:
        rel_path = str(file.resolve().relative_to(base_path.resolve()))
        entries.append(
            {
                "path": rel_path,
                "sha256": _sha256_file(file),
                "size_bytes": file.stat().st_size,
            }
        )

    signature_input = "|".join(f"{entry['path']}:{entry['sha256']}" for entry in entries)
    combined_sha256 = hashlib.sha256(signature_input.encode("utf-8")).hexdigest()

    return {
        "source_count": len(entries),
        "sources": entries,
        "combined_sha256": combined_sha256,
    }


def read_index_metadata(persist_path: Path) -> dict[str, Any] | None:
    metadata_path = persist_path / INDEX_METADATA_FILENAME
    if not metadata_path.exists() or not metadata_path.is_file():
        return None

    try:
        with metadata_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
    except Exception:
        return None

    return raw if isinstance(raw, dict) else None


def write_index_metadata(
    persist_path: Path,
    *,
    collection_name: str,
    embedding_model: str,
    collection_size: int,
    base_path: Path,
    docs_path: str | None,
    rebuild_mode: str,
) -> dict[str, Any]:
    persist_path.mkdir(parents=True, exist_ok=True)
    metadata_path = persist_path / INDEX_METADATA_FILENAME

    snapshot = build_sources_snapshot(base_path, docs_path)
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "collection_name": collection_name,
        "embedding_model": embedding_model,
        "collection_size": collection_size,
        "rebuild_mode": rebuild_mode,
        "source_snapshot": snapshot,
        "schema_version": 1,
    }

    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return payload


def validate_index_metadata(
    persist_path: Path,
    *,
    base_path: Path,
    docs_path: str | None,
) -> dict[str, Any]:
    metadata = read_index_metadata(persist_path)
    if not metadata:
        return {
            "is_valid": False,
            "reason": "missing_metadata",
            "expected_signature": None,
            "actual_signature": None,
        }

    snapshot = metadata.get("source_snapshot")
    expected_signature = None
    if isinstance(snapshot, dict):
        expected_signature = snapshot.get("combined_sha256")

    actual_snapshot = build_sources_snapshot(base_path, docs_path)
    actual_signature = actual_snapshot.get("combined_sha256")

    if not expected_signature:
        return {
            "is_valid": False,
            "reason": "invalid_metadata_format",
            "expected_signature": expected_signature,
            "actual_signature": actual_signature,
        }

    if expected_signature != actual_signature:
        return {
            "is_valid": False,
            "reason": "source_snapshot_changed",
            "expected_signature": expected_signature,
            "actual_signature": actual_signature,
        }

    return {
        "is_valid": True,
        "reason": None,
        "expected_signature": expected_signature,
        "actual_signature": actual_signature,
    }

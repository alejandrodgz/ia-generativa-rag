from __future__ import annotations

import shutil
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from rag_adm.main import app, reset_runtime_caches


@pytest.fixture
def isolated_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[Path, None, None]:
    project_root = Path(__file__).resolve().parents[1]

    shutil.copytree(project_root / "data", tmp_path / "data")

    monkeypatch.setattr("rag_adm.main.get_base_path", lambda: tmp_path)
    reset_runtime_caches()
    yield tmp_path
    reset_runtime_caches()


def test_ingest_document_updates_enrichment_status(isolated_repo: Path) -> None:
    client = TestClient(app)
    before = client.get("/enrichment/status").json()

    response = client.post(
        "/enrichment/document",
        json={
            "modulo_asignado": "ADM",
            "title": "Manual ADM regional",
            "content": "Este documento describe criterios adicionales de seguimiento, trazabilidad y soporte ADM.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extra_documents_count"] == before["extra_documents_count"] + 1

    status = client.get("/enrichment/status")
    assert status.status_code == 200
    assert status.json()["extra_documents_count"] == before["extra_documents_count"] + 1


def test_generate_synthetic_cases_persists_cases(isolated_repo: Path) -> None:
    client = TestClient(app)
    before = client.get("/metadata").json()

    response = client.post(
        "/enrichment/synthetic-cases",
        json={
            "cargo": "Coordinador experimental",
            "modulo_asignado": "ADM",
            "tipo_participante": "Productor",
            "descripcion_base": "Hace seguimiento a etapas y necesita trazabilidad contextual.",
            "count": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["generated_count"] == 2
    assert body["synthetic_cases_count"] == before["synthetic_cases_count"] + 2
    assert len(body["generated_ids"]) == 2

    status = client.get("/metadata")
    assert status.status_code == 200
    assert status.json()["synthetic_cases_count"] == before["synthetic_cases_count"] + 2


def test_upload_document_file_updates_enrichment_status(isolated_repo: Path) -> None:
    client = TestClient(app)
    before = client.get("/enrichment/status").json()

    response = client.post(
        "/enrichment/document-upload",
        files={"file": ("manual_adm.txt", b"Documento de prueba para contexto ADM y reglas operativas.", "text/plain")},
        data={"title": "Manual ADM por archivo", "modulo_asignado": "ADM"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extra_documents_count"] == before["extra_documents_count"] + 1

    status = client.get("/enrichment/status")
    assert status.status_code == 200
    assert status.json()["extra_documents_count"] == before["extra_documents_count"] + 1
from __future__ import annotations

from datetime import datetime, UTC
import io
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .knowledge_base import KnowledgeBase


USER_DOCS_DIR = Path("data/user_knowledge")
SYNTHETIC_CASES_FILE = Path("data/historico_sintetico.json")


def get_user_docs_dir(base_path: Path) -> Path:
    directory = (base_path / USER_DOCS_DIR).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_synthetic_cases_path(base_path: Path) -> Path:
    path = (base_path / SYNTHETIC_CASES_FILE).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def list_user_documents(base_path: Path) -> list[dict[str, Any]]:
    directory = get_user_docs_dir(base_path)
    documents: list[dict[str, Any]] = []
    for file in sorted(directory.glob("*.txt")):
        stat = file.stat()
        documents.append(
            {
                "name": file.name,
                "size_bytes": stat.st_size,
                "updated_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            }
        )
    return documents


def save_user_document(base_path: Path, title: str, content: str, modulo_asignado: str) -> dict[str, Any]:
    slug = _slugify(title)
    modulo = _slugify(modulo_asignado).upper()
    directory = get_user_docs_dir(base_path)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    file_path = directory / f"{timestamp}-{modulo}-{slug}.txt"
    file_path.write_text(content.strip() + "\n", encoding="utf-8")
    return {
        "file_name": file_path.name,
        "title": title.strip(),
        "modulo_asignado": modulo,
        "size_bytes": file_path.stat().st_size,
    }


def save_uploaded_document(
    base_path: Path,
    filename: str,
    content: bytes,
    modulo_asignado: str,
    title: str | None = None,
) -> dict[str, Any]:
    extracted_text = _extract_text_from_upload(filename, content)
    if not extracted_text.strip():
        raise ValueError("No se pudo extraer texto util del archivo.")

    final_title = title.strip() if title and title.strip() else Path(filename).stem
    return save_user_document(base_path, final_title, extracted_text, modulo_asignado)


def load_synthetic_cases(base_path: Path) -> list[dict[str, Any]]:
    file_path = get_synthetic_cases_path(base_path)
    if not file_path.exists():
        return []
    try:
        with file_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
    except Exception:
        return []
    return raw if isinstance(raw, list) else []


def append_synthetic_cases(base_path: Path, cases: list[dict[str, Any]]) -> int:
    file_path = get_synthetic_cases_path(base_path)
    existing = load_synthetic_cases(base_path)
    updated = existing + cases
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(updated, file, ensure_ascii=False, indent=2)
    return len(updated)


def generate_synthetic_cases(
    knowledge_base: KnowledgeBase,
    *,
    cargo: str,
    modulo_asignado: str,
    tipo_participante: str,
    descripcion_base: str,
    count: int,
    base_path: Path,
) -> list[dict[str, Any]]:
    reglas = [
        regla
        for regla in knowledge_base.politicas["reglas"]
        if regla["modulo"].lower() == modulo_asignado.lower()
        and regla["tipo_participante"].lower() == tipo_participante.lower()
    ]
    regla = reglas[0] if reglas else None
    rol = regla["rol_preferido"] if regla else "Invitado"
    permisos = list(regla["permisos"] if regla else [])

    existing_cases = load_synthetic_cases(base_path)
    start_index = len(existing_cases) + 1
    variants = [
        "Consulta operativa y seguimiento de procesos.",
        "Gestiona validaciones y revisa trazabilidad del modulo.",
        "Coordina tareas recurrentes y necesita contexto historico.",
        "Atiende solicitudes del equipo y documenta decisiones.",
    ]

    synthetic_cases: list[dict[str, Any]] = []
    for offset in range(count):
        suffix = variants[offset % len(variants)]
        description = f"{descripcion_base.strip()} {suffix}".strip()
        synthetic_cases.append(
            {
                "id": f"SYN-{_slugify(modulo_asignado).upper()}-{start_index + offset:03d}",
                "cargo": cargo.strip(),
                "modulo_asignado": modulo_asignado.strip(),
                "tipo_participante": tipo_participante.strip(),
                "descripcion_adicional": description,
                "rol": rol,
                "permisos": permisos,
            }
        )
    return synthetic_cases


def get_enrichment_status(base_path: Path) -> dict[str, Any]:
    docs = list_user_documents(base_path)
    synthetic_cases = load_synthetic_cases(base_path)
    return {
        "extra_documents_count": len(docs),
        "synthetic_cases_count": len(synthetic_cases),
        "extra_documents": docs,
    }


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "documento"


def _extract_text_from_upload(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="ignore")

    if suffix == ".pdf":
        try:
            import fitz

            text_parts: list[str] = []
            with fitz.open(stream=io.BytesIO(content), filetype="pdf") as pdf:
                for page in pdf:
                    text_parts.append(page.get_text())
            return "\n".join(part for part in text_parts if part.strip())
        except Exception as exc:
            raise ValueError("No se pudo leer el PDF cargado.") from exc

    raise ValueError("Formato no soportado. Usa .txt, .md o .pdf")
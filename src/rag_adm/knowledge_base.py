from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .enrichment import load_synthetic_cases


@dataclass(slots=True)
class KnowledgeBase:
    politicas: dict
    permisos: list[dict]
    historico: list[dict]

    @classmethod
    def load(cls, base_path: Path) -> "KnowledgeBase":
        data_dir = base_path / "data"
        with (data_dir / "politicas_acceso.json").open("r", encoding="utf-8") as file:
            politicas = json.load(file)
        with (data_dir / "catalogo_permisos.json").open("r", encoding="utf-8") as file:
            permisos = json.load(file)
        with (data_dir / "historico_configuraciones.json").open("r", encoding="utf-8") as file:
            historico = json.load(file)
        historico.extend(load_synthetic_cases(base_path))
        return cls(politicas=politicas, permisos=permisos, historico=historico)

    def permisos_validos(self) -> set[str]:
        return {permiso["nombre"] for permiso in self.permisos}

    def roles_validos(self) -> set[str]:
        return {rol["nombre"] for rol in self.politicas["roles"]}

    def to_vector_records(self) -> list[dict[str, Any]]:
        """Convierte el conocimiento estructurado en registros listos para indexar.

        Cada registro contiene `text` para embedding y `metadata` con claves planas
        compatibles con Chroma.
        """
        records: list[dict[str, Any]] = []

        for index, regla in enumerate(self.politicas["reglas"], start=1):
            text = (
                "Fuente: politica de acceso. "
                f"Modulo {regla['modulo']}. "
                f"Tipo de participante {regla['tipo_participante']}. "
                f"Rol preferido {regla['rol_preferido']}. "
                f"Permisos sugeridos: {', '.join(regla['permisos'])}."
            )
            records.append(
                {
                    "id": f"rule-{index}",
                    "text": text,
                    "metadata": {
                        "source_type": "regla",
                        "source_id": f"rule-{index}",
                        "modulo": regla["modulo"],
                        "tipo_participante": regla["tipo_participante"],
                        "rol": regla["rol_preferido"],
                        "payload_json": json.dumps(regla, ensure_ascii=False),
                    },
                }
            )

        for permiso in self.permisos:
            text = (
                "Fuente: catalogo de permisos. "
                f"Permiso {permiso['nombre']} del modulo {permiso['modulo']}. "
                f"Descripcion: {permiso['descripcion']}."
            )
            records.append(
                {
                    "id": f"perm-{permiso['nombre']}",
                    "text": text,
                    "metadata": {
                        "source_type": "permiso",
                        "source_id": permiso["nombre"],
                        "modulo": permiso["modulo"],
                        "tipo_participante": "",
                        "rol": "",
                        "payload_json": json.dumps(permiso, ensure_ascii=False),
                    },
                }
            )

        for caso in self.historico:
            text = (
                "Fuente: historico de configuraciones. "
                f"Caso {caso['id']}. "
                f"Cargo {caso['cargo']}. "
                f"Modulo {caso['modulo_asignado']}. "
                f"Tipo de participante {caso['tipo_participante']}. "
                f"Rol asignado {caso['rol']}. "
                f"Permisos: {', '.join(caso['permisos'])}. "
                f"Descripcion adicional: {caso.get('descripcion_adicional', '')}."
            )
            records.append(
                {
                    "id": f"hist-{caso['id']}",
                    "text": text,
                    "metadata": {
                        "source_type": "historico",
                        "source_id": caso["id"],
                        "modulo": caso["modulo_asignado"],
                        "tipo_participante": caso["tipo_participante"],
                        "rol": caso["rol"],
                        "payload_json": json.dumps(caso, ensure_ascii=False),
                    },
                }
            )

        return records

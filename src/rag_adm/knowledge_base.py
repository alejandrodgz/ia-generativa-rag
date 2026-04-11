from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


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
        return cls(politicas=politicas, permisos=permisos, historico=historico)

    def permisos_validos(self) -> set[str]:
        return {permiso["nombre"] for permiso in self.permisos}

    def roles_validos(self) -> set[str]:
        return {rol["nombre"] for rol in self.politicas["roles"]}

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .knowledge_base import KnowledgeBase
from .llm_client import MockLLMClient
from .models import RecommendationRequest, RecommendationResponse
from .recommender import RolePermissionRecommender
from .retriever import HybridRetriever, JaccardRetriever, VectorRetriever
from .settings import HybridSettings, Settings


@dataclass(slots=True)
class GoldenCase:
    case_id: str
    cargo: str
    modulo_asignado: str
    tipo_participante: str
    descripcion_adicional: str
    expected_role: str
    must_have_permissions: list[str]
    stability_group: str


@dataclass(slots=True)
class ModeMetrics:
    mode: str
    total_cases: int
    role_accuracy: float
    permission_coverage: float
    confidence_stability: float


def load_golden_cases(dataset_path: Path) -> list[GoldenCase]:
    with dataset_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    cases: list[GoldenCase] = []
    for item in raw:
        cases.append(
            GoldenCase(
                case_id=str(item["id"]),
                cargo=str(item["cargo"]),
                modulo_asignado=str(item["modulo_asignado"]),
                tipo_participante=str(item["tipo_participante"]),
                descripcion_adicional=str(item.get("descripcion_adicional", "")),
                expected_role=str(item["expected_role"]),
                must_have_permissions=[str(permission) for permission in item["must_have_permissions"]],
                stability_group=str(item["stability_group"]),
            )
        )
    return cases


def _base_vector_settings(base_path: Path) -> Settings:
    return Settings(
        llm_api_key=None,
        llm_base_url=None,
        llm_model=None,
        llm_timeout_seconds=20.0,
        retriever_mode="vector",
        vector_store_path=str(base_path / "data" / "chroma_db"),
        vector_collection_name="adm_knowledge_base",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        knowledge_docs_path=None,
        vector_rebuild_index=False,
        vector_rebuild_policy="incremental",
    )


def _base_hybrid_settings() -> HybridSettings:
    return HybridSettings(
        enabled=True,
        k_similar_cases=5,
        affinity_threshold=0.0,
        affinity_boost_factor=1.2,
        vector_weight=0.7,
        rules_exact_match_only=True,
    )


def build_mode_recommenders(base_path: Path) -> dict[str, RolePermissionRecommender]:
    kb = KnowledgeBase.load(base_path)
    llm = MockLLMClient()

    jaccard = JaccardRetriever(kb)
    vector_settings = _base_vector_settings(base_path)
    vector = VectorRetriever(kb, vector_settings, base_path)
    hybrid = HybridRetriever(jaccard, vector, _base_hybrid_settings())

    return {
        "jaccard": RolePermissionRecommender(kb, llm, jaccard),
        "vector": RolePermissionRecommender(kb, llm, vector),
        "hybrid": RolePermissionRecommender(kb, llm, hybrid),
    }


def _recommend(recommender: RolePermissionRecommender, case: GoldenCase) -> RecommendationResponse:
    request = RecommendationRequest(
        cargo=case.cargo,
        modulo_asignado=case.modulo_asignado,
        tipo_participante=case.tipo_participante,
        descripcion_adicional=case.descripcion_adicional,
    )
    return recommender.recommend(request)


def _compute_confidence_stability(confidence_by_group: dict[str, list[str]]) -> float:
    group_scores: list[float] = []
    for values in confidence_by_group.values():
        if not values:
            continue
        counts = Counter(values)
        group_scores.append(max(counts.values()) / len(values))
    return sum(group_scores) / len(group_scores) if group_scores else 0.0


def _evaluate_mode(
    mode: str,
    recommender: RolePermissionRecommender,
    cases: list[GoldenCase],
) -> tuple[ModeMetrics, list[dict[str, Any]]]:
    role_hits = 0
    permission_coverages: list[float] = []
    confidence_by_group: dict[str, list[str]] = defaultdict(list)
    per_case: list[dict[str, Any]] = []

    for case in cases:
        response = _recommend(recommender, case)

        role_ok = response.rol_recomendado == case.expected_role
        if role_ok:
            role_hits += 1

        required = set(case.must_have_permissions)
        predicted = set(response.permisos_recomendados)
        coverage = (len(required & predicted) / len(required)) if required else 1.0
        permission_coverages.append(coverage)
        confidence_by_group[case.stability_group].append(response.nivel_confianza)

        per_case.append(
            {
                "case_id": case.case_id,
                "expected_role": case.expected_role,
                "predicted_role": response.rol_recomendado,
                "role_ok": role_ok,
                "required_permissions": case.must_have_permissions,
                "predicted_permissions": response.permisos_recomendados,
                "permission_coverage": coverage,
                "confidence": response.nivel_confianza,
            }
        )

    metrics = ModeMetrics(
        mode=mode,
        total_cases=len(cases),
        role_accuracy=(role_hits / len(cases) if cases else 0.0),
        permission_coverage=(sum(permission_coverages) / len(permission_coverages) if permission_coverages else 0.0),
        confidence_stability=_compute_confidence_stability(confidence_by_group),
    )
    return metrics, per_case


def evaluate_modes(base_path: Path, dataset_path: Path) -> tuple[list[ModeMetrics], dict[str, list[dict[str, Any]]]]:
    cases = load_golden_cases(dataset_path)
    recommenders = build_mode_recommenders(base_path)

    metrics: list[ModeMetrics] = []
    raw_results: dict[str, list[dict[str, Any]]] = {}

    for mode, recommender in recommenders.items():
        mode_metrics, per_case = _evaluate_mode(mode, recommender, cases)
        metrics.append(mode_metrics)
        raw_results[mode] = per_case

    return metrics, raw_results


def render_markdown_report(metrics: list[ModeMetrics]) -> str:
    by_mode = {entry.mode: entry for entry in metrics}

    def _fmt(value: float) -> str:
        return f"{value:.3f}"

    lines = [
        "# Reporte de Calidad de Retrieval (Fase 4)",
        "",
        "Comparativa automática de modos de retrieval sobre dataset dorado ADM.",
        "",
        "| Modo | Casos | Precision Rol | Cobertura Permisos | Estabilidad Confianza |",
        "|---|---:|---:|---:|---:|",
    ]

    for mode in ["jaccard", "vector", "hybrid"]:
        entry = by_mode.get(mode)
        if not entry:
            continue
        lines.append(
            "| "
            f"{mode} | {entry.total_cases} | {_fmt(entry.role_accuracy)} | "
            f"{_fmt(entry.permission_coverage)} | {_fmt(entry.confidence_stability)} |"
        )

    if by_mode:
        best_role = max(by_mode.values(), key=lambda item: item.role_accuracy)
        best_permissions = max(by_mode.values(), key=lambda item: item.permission_coverage)
        best_stability = max(by_mode.values(), key=lambda item: item.confidence_stability)

        lines.extend(
            [
                "",
                "## Resumen",
                "",
                f"- Mejor precision de rol: {best_role.mode} ({_fmt(best_role.role_accuracy)})",
                f"- Mejor cobertura de permisos: {best_permissions.mode} ({_fmt(best_permissions.permission_coverage)})",
                f"- Mejor estabilidad de confianza: {best_stability.mode} ({_fmt(best_stability.confidence_stability)})",
            ]
        )

    return "\n".join(lines)

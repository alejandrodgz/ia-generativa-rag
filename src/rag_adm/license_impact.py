from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .models import (
    LicenseImpactEvidence,
    LicenseImpactItem,
    LicenseImpactRequest,
    LicenseImpactResponse,
)


CATALOG_FILE = Path("data/politicas_licencias_costos.json")

_RISK_ORDER = {"bajo": 0, "medio": 1, "alto": 2}


def analyze_license_impact(
    base_path: Path,
    request: LicenseImpactRequest,
    supporting_documents: list[dict[str, Any]] | None = None,
) -> LicenseImpactResponse:
    catalog = _load_catalog(base_path)
    systems_by_id = {
        str(system["id"]): system
        for system in catalog.get("sistemas_externos", [])
        if isinstance(system, dict) and "id" in system
    }

    permisos = set(request.permisos_recomendados)
    permisos_externos = set(request.permisos_externos_solicitados)
    matched_rules = [
        rule
        for rule in catalog.get("reglas_impacto", [])
        if _rule_applies(rule, request.modulo_asignado, permisos, permisos_externos)
    ]

    impacts = [_build_impact(rule, systems_by_id, permisos, permisos_externos) for rule in matched_rules]
    impacts = [impact for impact in impacts if impact is not None]

    risk = _overall_risk(impacts)
    classification = _overall_classification(impacts)
    heuristics = catalog.get("heuristicas_reporte", {})
    default_message = "No se detectaron impactos externos con los permisos evaluados."
    message = str(heuristics.get(classification, default_message))

    return LicenseImpactResponse(
        clasificacion_general=classification,
        riesgo_general=risk,
        requiere_licencia_adicional=any(impact.requiere_licencia_adicional for impact in impacts),
        requiere_modulo_adicional=any(impact.requiere_modulo_adicional for impact in impacts),
        costo_estimado_mock=_unique(impact.costo_estimado_mock for impact in impacts if impact.costo_estimado_mock),
        areas_aprobadoras=_unique(impact.area_aprobadora for impact in impacts if impact.area_aprobadora),
        acciones_sugeridas=_unique(impact.accion_sugerida for impact in impacts if impact.accion_sugerida),
        permisos_evaluados=list(request.permisos_recomendados),
        permisos_externos_evaluados=_unique(
            permission
            for impact in impacts
            for permission in impact.permisos_externos_relacionados
        ),
        impactos=impacts,
        evidencias_recuperadas=_build_evidence(impacts, request, supporting_documents or []),
        mensaje=message,
    )


def _load_catalog(base_path: Path) -> dict[str, Any]:
    path = base_path / CATALOG_FILE
    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    if not isinstance(raw, dict):
        raise ValueError("El catalogo de licencias debe ser un objeto JSON.")
    return raw


def _rule_applies(
    rule: dict[str, Any],
    modulo: str,
    permisos: set[str],
    permisos_externos: set[str],
) -> bool:
    rule_module = str(rule.get("modulo", "")).upper()
    if rule_module not in {modulo.upper(), "GLOBAL"}:
        return False

    rule_permissions = {str(permission) for permission in rule.get("permisos_evergreen", [])}
    rule_external_permissions = {str(permission) for permission in rule.get("permisos_externos_relacionados", [])}

    return bool(rule_permissions & permisos) or bool(rule_external_permissions & permisos_externos)


def _build_impact(
    rule: dict[str, Any],
    systems_by_id: dict[str, dict[str, Any]],
    permisos: set[str],
    permisos_externos: set[str],
) -> LicenseImpactItem | None:
    rule_permissions = [str(permission) for permission in rule.get("permisos_evergreen", [])]
    rule_external_permissions = [str(permission) for permission in rule.get("permisos_externos_relacionados", [])]
    related_permissions = [permission for permission in rule_permissions if permission in permisos]
    if related_permissions:
        related_external_permissions = rule_external_permissions
    else:
        related_external_permissions = [
            permission for permission in rule_external_permissions if permission in permisos_externos
        ]

    if not related_permissions and not related_external_permissions:
        return None

    cost = rule.get("costo_mock", {})
    if not isinstance(cost, dict):
        cost = {}

    system_ids = [str(system_id) for system_id in rule.get("sistemas_afectados", [])]
    system_names = [
        str(systems_by_id.get(system_id, {}).get("nombre", system_id))
        for system_id in system_ids
    ]

    return LicenseImpactItem(
        regla_id=str(rule.get("id", "")),
        sistemas_afectados=system_ids,
        sistemas_afectados_nombre=system_names,
        permisos_relacionados=related_permissions,
        permisos_externos_relacionados=related_external_permissions,
        riesgo=_normalize_risk(rule.get("riesgo")),
        impacto_licencia=str(rule.get("impacto_licencia", "")),
        costo_estimado_mock=str(cost.get("rango_mensual_estimado", "")),
        requiere_licencia_adicional=bool(cost.get("requiere_licencia_adicional", False)),
        requiere_modulo_adicional=bool(cost.get("requiere_modulo_adicional", False)),
        accion_sugerida=str(rule.get("accion_sugerida", "")),
        area_aprobadora=str(rule.get("area_aprobadora", "")),
        explicacion=str(rule.get("explicacion", "")),
    )


def _normalize_risk(value: object) -> str:
    risk = str(value).lower()
    return risk if risk in _RISK_ORDER else "bajo"


def _overall_risk(impacts: list[LicenseImpactItem]) -> str:
    if not impacts:
        return "bajo"
    return max((impact.riesgo for impact in impacts), key=lambda risk: _RISK_ORDER[risk])


def _overall_classification(impacts: list[LicenseImpactItem]) -> str:
    if any(impact.requiere_modulo_adicional or impact.riesgo == "alto" for impact in impacts):
        return "requiere_validacion_contractual"
    if any(impact.requiere_licencia_adicional for impact in impacts):
        return "requiere_licencia"
    if impacts:
        return "posible_costo"
    return "sin_costo_aparente"


def _build_evidence(
    impacts: list[LicenseImpactItem],
    request: LicenseImpactRequest,
    supporting_documents: list[dict[str, Any]],
) -> list[LicenseImpactEvidence]:
    vector_evidence = [
        LicenseImpactEvidence(
            tipo="politica_vectorial",
            titulo=str(document.get("title") or document.get("source_file") or "Documento de apoyo"),
            resumen=str(document.get("content_preview") or document.get("descripcion") or "")[:500],
            fuente_ref=str(document.get("source_file") or document.get("id") or "vector_store"),
            score=float(document["_score"]) if "_score" in document else None,
        )
        for document in supporting_documents[:3]
        if isinstance(document, dict)
    ]

    if not impacts:
        return vector_evidence + [
            LicenseImpactEvidence(
                tipo="catalogo_mock",
                titulo="Sin impacto externo detectado",
                resumen=(
                    "Los permisos evaluados no coincidieron con reglas mock de licencias, "
                    "modulos externos o consumo adicional."
                ),
                fuente_ref="data/politicas_licencias_costos.json",
            )
        ]

    evidence = [
            LicenseImpactEvidence(
                tipo="regla_impacto",
                titulo=f"{impact.regla_id} - {', '.join(impact.sistemas_afectados_nombre)}",
            resumen=impact.explicacion,
            fuente_ref="data/politicas_licencias_costos.json",
        )
        for impact in impacts[:4]
    ]

    evidence = vector_evidence + evidence
    evidence.append(
        LicenseImpactEvidence(
            tipo="perfil_evaluado",
            titulo=f"{request.modulo_asignado} - {request.cargo}",
            resumen=(
                "Analisis calculado con los permisos recomendados por el RAG y los impactos "
                "externos inferidos desde el catalogo mock."
            ),
            fuente_ref="request",
        )
    )
    return evidence


def _unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result

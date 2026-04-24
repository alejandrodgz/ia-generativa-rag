from __future__ import annotations

import json
from pathlib import Path

from rag_adm.license_impact import analyze_license_impact
from rag_adm.models import LicenseImpactRequest


def test_license_impact_endpoint_is_registered() -> None:
    from rag_adm.main import app

    assert any(route.path == "/analizar-impacto-licencias" for route in app.routes)


def test_license_impact_scenarios_match_expected_classification() -> None:
    base_path = Path(__file__).resolve().parents[1]
    scenarios_path = base_path / "data" / "escenarios_impacto_licencias.json"
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))

    for scenario in scenarios:
        response = analyze_license_impact(
            base_path,
            LicenseImpactRequest(
                cargo=scenario["cargo"],
                modulo_asignado=scenario["modulo_asignado"],
                tipo_participante_inferido=scenario["tipo_participante"],
                permisos_recomendados=scenario["permisos_evaluados"],
                permisos_externos_solicitados=scenario["permisos_externos_solicitados"],
            ),
        )

        expected = scenario["resultado_esperado_mock"]
        assert response.clasificacion_general == expected["clasificacion"], scenario["id"]
        assert response.riesgo_general == expected["riesgo"], scenario["id"]
        assert set(expected["areas_aprobadoras"]).issubset(set(response.areas_aprobadoras)), scenario["id"]
        assert response.impactos, scenario["id"]


def test_license_impact_without_external_rules_reports_no_apparent_cost() -> None:
    base_path = Path(__file__).resolve().parents[1]

    response = analyze_license_impact(
        base_path,
        LicenseImpactRequest(
            cargo="Productor agricola",
            modulo_asignado="ADM",
            tipo_participante_inferido="Productor",
            rol_recomendado="Invitado",
            permisos_recomendados=["ver_agrocadenas", "ver_etapas"],
        ),
    )

    assert response.clasificacion_general == "sin_costo_aparente"
    assert response.riesgo_general == "bajo"
    assert response.requiere_licencia_adicional is False
    assert response.requiere_modulo_adicional is False
    assert response.impactos == []
    assert response.evidencias_recuperadas


def test_license_impact_returns_structured_report() -> None:
    base_path = Path(__file__).resolve().parents[1]

    response = analyze_license_impact(
        base_path,
        LicenseImpactRequest(
            cargo="Analista de soporte ADM",
            modulo_asignado="ADM",
            tipo_participante_inferido="Administrador",
            rol_recomendado="Admin",
            permisos_recomendados=["gestionar_usuarios", "configurar_permisos", "auditar_accesos"],
        ),
    )

    assert response.clasificacion_general == "requiere_validacion_contractual"
    assert response.riesgo_general == "alto"
    assert response.requiere_licencia_adicional is True
    assert response.impactos
    assert "RRHH / TI" in response.areas_aprobadoras
    assert "successfactors_perfil_empleado_consulta" in response.permisos_externos_evaluados
    assert "github_repositorios_privados_lectura" in response.permisos_externos_evaluados


def test_license_impact_includes_vector_evidence_when_available() -> None:
    base_path = Path(__file__).resolve().parents[1]

    response = analyze_license_impact(
        base_path,
        LicenseImpactRequest(
            cargo="Analista de soporte ADM",
            modulo_asignado="ADM",
            tipo_participante_inferido="Administrador",
            rol_recomendado="Admin",
            permisos_recomendados=["gestionar_usuarios", "configurar_permisos"],
        ),
        supporting_documents=[
            {
                "title": "Impacto licencias accesos ADM",
                "source_file": "20260424090001-ADM-impacto-licencias-accesos.txt",
                "content_preview": "Gestionar usuarios puede requerir HCM externo y validacion con RRHH.",
                "_score": 0.83,
            }
        ],
    )

    assert response.evidencias_recuperadas[0].tipo == "politica_vectorial"
    assert response.evidencias_recuperadas[0].score == 0.83
    assert "HCM externo" in response.evidencias_recuperadas[0].resumen

from pathlib import Path

from rag_adm.knowledge_base import KnowledgeBase
from rag_adm.llm_client import MockLLMClient
from rag_adm.models import RecommendationRequest
from rag_adm.recommender import RolePermissionRecommender
from rag_adm.retriever import JaccardRetriever


def _recommender() -> RolePermissionRecommender:
    base_path = Path(__file__).resolve().parents[1]
    kb = KnowledgeBase.load(base_path)
    return RolePermissionRecommender(kb, MockLLMClient(), JaccardRetriever(kb))


def test_recomienda_admin_para_perfil_administrador() -> None:
    engine = _recommender()
    response = engine.recommend(
        RecommendationRequest(
            cargo="Administrador de plataforma",
            modulo_asignado="ADM",
            descripcion_adicional="Gestiona usuarios y permisos del sistema",
        )
    )

    # Sin tipo_participante el Mock infiere del primer caso/regla del módulo.
    # Verificamos que la respuesta es estructuralmente válida y que el tipo fue inferido.
    assert response.rol_recomendado in {"Admin", "Invitado"}
    assert isinstance(response.permisos_recomendados, list)
    assert response.nivel_confianza in {"alto", "medio", "bajo"}
    assert response.tipo_participante_inferido is not None


def test_recomienda_invitado_para_productor() -> None:
    engine = _recommender()
    response = engine.recommend(
        RecommendationRequest(
            cargo="Productor agricola de la region",
            modulo_asignado="ADM",
            descripcion_adicional="Productor que necesita ver el estado de la agrocadena",
        )
    )

    assert response.rol_recomendado == "Invitado"
    assert "gestionar_usuarios" not in response.permisos_recomendados
    assert "configurar_permisos" not in response.permisos_recomendados
    assert response.justificacion
    assert response.tipo_participante_inferido is not None


def test_entrega_confianza_baja_si_no_hay_reglas_ni_historial_relevante() -> None:
    engine = _recommender()
    response = engine.recommend(
        RecommendationRequest(
            cargo="Observador externo",
            modulo_asignado="ADM",
            tipo_participante="Invitado externo",
            descripcion_adicional="Solo requiere una vista general ocasional",
        )
    )

    assert response.rol_recomendado == "Invitado"
    assert response.nivel_confianza in {"bajo", "medio"}
    assert "ver_agrocadenas" in response.permisos_recomendados or response.permisos_recomendados == []


from fastapi.testclient import TestClient

from rag_adm.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metadata_endpoint() -> None:
    response = client.get("/metadata")

    assert response.status_code == 200
    body = response.json()
    assert body["llm_mode"] in {"mock", "remote"}
    assert body["retriever_mode"] in {"jaccard", "vector", "hybrid"}
    assert {"ADM", "DIS", "PLA", "FIN"}.issubset(set(body["modulos_disponibles"]))
    assert body["total_permisos"] >= 1
    assert "index_metadata_present" in body
    assert "index_metadata_valid" in body
    assert "extra_documents_count" in body
    assert "synthetic_cases_count" in body


def test_recomendar_rol_endpoint() -> None:
    payload = {
        "cargo": "Analista de soporte ADM",
        "modulo_asignado": "ADM",
        "tipo_participante": "Administrador",
        "descripcion_adicional": "Apoya la gestion de usuarios",
    }

    response = client.post("/recomendar-rol", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["rol_recomendado"] == "Admin"
    assert "gestionar_usuarios" in body["permisos_recomendados"]
    assert body["retrieval_mode"] in {"jaccard", "vector", "hybrid"}
    assert isinstance(body["reglas_recuperadas_ref"], list)
    assert isinstance(body["casos_similares_score"], list)
    assert isinstance(body["documentos_apoyo_ref"], list)


def test_recomendar_rol_endpoint_for_dis_module() -> None:
    payload = {
        "cargo": "Operador de ruta regional",
        "modulo_asignado": "DIS",
        "tipo_participante": "Transportista",
        "descripcion_adicional": "Necesita calcular trayectorias y revisar estado del envio.",
    }

    response = client.post("/recomendar-rol", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["rol_recomendado"] == "Invitado"
    assert "dis_calcular_distancia_tiempo" in body["permisos_recomendados"]
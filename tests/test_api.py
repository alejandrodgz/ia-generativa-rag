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
    assert "ADM" in body["modulos_disponibles"]
    assert body["total_permisos"] >= 1


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
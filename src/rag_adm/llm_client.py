from __future__ import annotations

from dataclasses import dataclass

import httpx

from .llm_parser import LLMDecision, LLMDecisionError, parse_llm_response
from .models import PromptMessage
from .prompt_builder import build_messages
from .recommender import PromptBundle
from .settings import Settings


@dataclass(slots=True)
class MockLLMClient:
    """Cliente determinístico para pruebas y modo mock.

    Toma una decision basada en las reglas y casos del bundle, sin llamar a ningun LLM externo.
    Actua como fallback cuando RemoteLLMClient falla.
    """

    def complete(
        self,
        bundle: PromptBundle,
        roles_validos: set[str],
        permisos_validos: set[str],
    ) -> LLMDecision:
        reglas = bundle.reglas_relevantes
        casos = bundle.casos_similares

        rol = reglas[0]["rol_preferido"] if reglas else "Invitado"
        if rol not in roles_validos:
            rol = "Invitado"

        permisos_candidatos = reglas[0]["permisos"] if reglas else []
        permisos = [p for p in permisos_candidatos if p in permisos_validos][:5]

        if reglas and casos and casos[0].get("_score", 0) >= 0.4:
            confianza = "alto"
        elif reglas or (casos and casos[0].get("_score", 0) >= 0.2):
            confianza = "medio"
        else:
            confianza = "bajo"

        fuentes = []
        if reglas:
            fuentes.append(f"la politica para modulo {reglas[0]['modulo']} y participante {reglas[0]['tipo_participante']}")
        if casos:
            fuentes.append(f"{len(casos)} casos similares del historico")
        fuentes_texto = " y ".join(fuentes) if fuentes else "las reglas base del dominio ADM"

        justificacion = (
            f"Se recomienda el rol {rol} basandose en {fuentes_texto}. "
            f"El nivel de confianza es {confianza} segun la coincidencia del perfil con el dominio registrado."
        )

        return LLMDecision(
            rol_recomendado=rol,
            permisos_recomendados=permisos,
            justificacion=justificacion,
            nivel_confianza=confianza,
        )


class RemoteLLMClient:
    def __init__(self, settings: Settings, fallback: MockLLMClient | None = None) -> None:
        self.settings = settings
        self.fallback = fallback or MockLLMClient()

    def complete(
        self,
        bundle: PromptBundle,
        roles_validos: set[str],
        permisos_validos: set[str],
    ) -> LLMDecision:
        messages = build_messages(bundle, roles_validos, permisos_validos)
        try:
            response_text = self._call_remote(messages)
            if response_text:
                return parse_llm_response(response_text, roles_validos, permisos_validos)
        except (LLMDecisionError, Exception):
            pass
        return self.fallback.complete(bundle, roles_validos, permisos_validos)

    def _call_remote(self, messages: list[PromptMessage]) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.llm_model,
            "messages": [message.model_dump() for message in messages],
            "temperature": 0.2,
        }
        endpoint = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        return body["choices"][0]["message"]["content"]


def build_llm_client(settings: Settings) -> MockLLMClient | RemoteLLMClient:
    if settings.llm_mode == "remote":
        return RemoteLLMClient(settings)
    return MockLLMClient()


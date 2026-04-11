from __future__ import annotations

from dataclasses import dataclass

import httpx

from .models import PromptMessage
from .prompt_builder import build_messages
from .recommender import PromptBundle
from .settings import Settings


@dataclass(slots=True)
class MockLLMClient:
    def complete(self, bundle: PromptBundle, rol: str, permisos: list[str], confianza: str) -> str:
        fuentes = []
        if bundle.reglas_relevantes:
            regla = bundle.reglas_relevantes[0]
            fuentes.append(
                f"la politica para modulo {regla['modulo']} y participante {regla['tipo_participante']}"
            )
        if bundle.casos_similares:
            fuentes.append(f"{len(bundle.casos_similares)} casos similares del historico")

        fuentes_texto = " y ".join(fuentes) if fuentes else "las reglas base del dominio ADM"
        permisos_texto = ", ".join(permisos) if permisos else "sin permisos adicionales"
        return (
            f"Se recomienda asignar el rol {rol} con los permisos {permisos_texto}. "
            f"La recomendacion se basa en {fuentes_texto}. "
            f"El nivel de confianza estimado es {confianza} segun la coincidencia del perfil con el dominio registrado."
        )


class RemoteLLMClient:
    def __init__(self, settings: Settings, fallback: MockLLMClient | None = None) -> None:
        self.settings = settings
        self.fallback = fallback or MockLLMClient()

    def complete(self, bundle: PromptBundle, rol: str, permisos: list[str], confianza: str) -> str:
        messages = build_messages(bundle, rol, permisos, confianza)
        try:
            response_text = self._call_remote(messages)
            if response_text:
                return response_text.strip()
        except Exception:
            pass
        return self.fallback.complete(bundle, rol, permisos, confianza)

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

from typing import Literal

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    cargo: str = Field(min_length=1, max_length=100)
    modulo_asignado: str = Field(min_length=1, max_length=20)
    tipo_participante: str = Field(min_length=1, max_length=100)
    descripcion_adicional: str | None = Field(default=None, max_length=500)


class RecommendationResponse(BaseModel):
    rol_recomendado: Literal["Admin", "Invitado"]
    permisos_recomendados: list[str]
    justificacion: str
    nivel_confianza: Literal["alto", "medio", "bajo"]
    casos_similares_ref: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"]


class MetadataResponse(BaseModel):
    llm_mode: Literal["mock", "remote"]
    roles_disponibles: list[str]
    modulos_disponibles: list[str]
    tipos_participante_disponibles: list[str]
    total_permisos: int
    total_casos_historicos: int


class PromptMessage(BaseModel):
    role: Literal["system", "user"]
    content: str

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CasoEntrada(BaseModel):
    descripcion: str = Field(
        ...,
        min_length=10,
        max_length=1500,
        description="Descripción de la situación o consulta de la persona ciclista.",
    )
    localidad: Optional[str] = Field(
        default=None,
        max_length=80,
        description="Localidad de Bogotá relacionada con el caso, si se conoce.",
    )
    tipo: Literal["ruta", "incidente", "consulta"] = "consulta"


class AnalisisCaso(BaseModel):
    id_caso: Optional[int] = None
    categoria: Literal[
        "infraestructura",
        "orientacion de ruta",
        "seguridad vial",
        "consulta general",
    ]
    nivel_riesgo: Literal["bajo", "medio", "alto"]
    resumen: str
    es_suficiente: bool = True
    inconsistencias: str = ""
    observaciones_imagen: str = ""
    preguntas_aclaracion: List[str] = Field(default_factory=list)
    recomendaciones: List[str] = Field(default_factory=list)
    agentes_ejecutados: List[str] = Field(default_factory=list)
import json
import os
import unicodedata
from typing import List, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pydantic import BaseModel, Field

from .agentes import ejecutar_analisis
from .database import (
    crear_tabla,
    guardar_analisis,
    listar_casos,
    obtener_caso,
)
from .mapas import buscar_lugares_bicicleta
from .schemas import CasoEntrada


load_dotenv()

app = FastAPI(
    title="BiciCerca Bogotá",
    description="API para orientar a personas que usan bicicleta por Bogotá.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

crear_tabla()


class MensajeChat(BaseModel):
    rol: Literal["usuario", "asistente"]
    texto: str = Field(..., min_length=1, max_length=6000)


class PreguntaChat(BaseModel):
    pregunta: str = Field(..., min_length=2, max_length=1000)
    historial: List[MensajeChat] = Field(default_factory=list)


def normalizar_texto(texto: str) -> str:
    """Pasa el texto a minúsculas y quita tildes para detectar la intención."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def pregunta_por_lugares_bicicleta(pregunta: str) -> bool:
    """
    Activa el mapa cuando la persona pide encontrar lugares.
    Mencionar un taller al hacer una pregunta de seguridad no basta.
    """
    texto = normalizar_texto(pregunta)

    intencion_de_busqueda = (
        "donde hay",
        "donde encuentro",
        "donde puedo encontrar",
        "buscar",
        "busca",
        "encuentra",
        "cerca",
        "cercano",
        "cercana",
        "lugares",
        "talleres",
        "tiendas",
        "bicicleterias",
        "direccion de",
        "ubicacion de",
    )

    tema_bicicleta = (
        "bicicleta",
        "bicicletas",
        "bici",
        "cicla",
        "taller",
        "bicicleteria",
        "reparacion",
        "mecanico",
    )

    quiere_buscar = any(frase in texto for frase in intencion_de_busqueda)
    trata_de_bicicletas = any(termino in texto for termino in tema_bicicleta)

    return quiere_buscar and trata_de_bicicletas


def crear_lista_lugares(resultado_mapa: dict) -> str:
    """Prepara una sola lista de lugares para mostrarla en el chat."""
    lugares = resultado_mapa.get("lugares", [])

    if not lugares:
        return ""

    lineas = ["\n\n**Lugares relacionados con bicicletas encontrados:**"]

    for lugar in lugares:
        nombre = lugar.get("nombre", "Negocio relacionado con bicicletas")
        direccion = lugar.get(
            "direccion",
            "La fuente no proporcionó una dirección.",
        )
        distancia = lugar.get("distancia_metros")
        enlace = lugar.get("enlace_mapa", "")

        linea = f"\n- **{nombre}** — {direccion}"

        if distancia is not None:
            kilometros = distancia / 1000
            linea += (
                f" — aproximadamente {kilometros:.1f} km "
                "desde el punto de referencia de la localidad"
            )

        if enlace:
            linea += f" — [Abrir ubicación en el mapa]({enlace})"

        lineas.append(linea)

    lineas.append(
        "\n\nLa fuente clasifica estos lugares como relacionados con bicicletas, "
        "pero no confirma que ofrezcan reparación. Verifica directamente "
        "el servicio antes de desplazarte."
    )

    return "".join(lineas)


@app.get("/")
def inicio():
    return {
        "mensaje": "Bienvenido a BiciCerca Bogotá",
        "estado": "API funcionando",
    }


@app.get("/salud")
def verificar_estado():
    return {"estado": "ok"}


@app.post("/casos/recibir")
def recibir_caso(caso: CasoEntrada):
    return {
        "estado": "recibido",
        "datos": caso.model_dump(),
    }


@app.post("/casos/analizar")
async def analizar_caso(
    descripcion: str = Form(..., min_length=10, max_length=1500),
    localidad: str = Form(""),
    tipo: Literal["ruta", "incidente", "consulta"] = Form("consulta"),
    imagen: UploadFile | None = File(None),
):
    imagen_bytes = None
    imagen_mime = None

    if imagen is not None and imagen.filename:
        tipos_permitidos = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        if imagen.content_type not in tipos_permitidos:
            raise HTTPException(
                status_code=415,
                detail="La imagen debe ser JPG, PNG o WebP.",
            )

        imagen_bytes = await imagen.read(8 * 1024 * 1024 + 1)

        if len(imagen_bytes) > 8 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="La imagen debe pesar máximo 8 MB.",
            )

        imagen_mime = imagen.content_type
        await imagen.close()

    localidad = localidad.strip() or "Bogotá"

    try:
        resultado = ejecutar_analisis(
            descripcion=descripcion,
            localidad=localidad,
            tipo=tipo,
            imagen_bytes=imagen_bytes,
            imagen_mime=imagen_mime,
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo analizar el caso: {error}",
        ) from error

    # La imagen se usa para el análisis, pero no se devuelve en la respuesta.
    resultado.pop("imagen_bytes", None)
    resultado.pop("imagen_mime", None)

    id_caso = guardar_analisis(
        descripcion=descripcion,
        localidad=localidad,
        tipo=tipo,
        resultado=resultado,
    )

    return {
        "id_caso": id_caso,
        **resultado,
    }


@app.get("/casos")
def consultar_casos():
    return listar_casos()


@app.get("/casos/{id_caso}")
def consultar_caso(id_caso: int):
    caso = obtener_caso(id_caso)

    if caso is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un caso con ese identificador.",
        )

    return caso


@app.post("/casos/{id_caso}/chat")
def chatear_sobre_caso(id_caso: int, datos: PreguntaChat):
    caso = obtener_caso(id_caso)

    if caso is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el caso para esta conversación.",
        )

    clave = os.getenv("GEMINI_API_KEY")

    if not clave:
        raise HTTPException(
            status_code=503,
            detail="No se encontró GEMINI_API_KEY en el archivo .env.",
        )

    consultar_mapa = pregunta_por_lugares_bicicleta(datos.pregunta)
    resultado_mapa = None

    if consultar_mapa:
        try:
            resultado_mapa = buscar_lugares_bicicleta(
                localidad=str(caso["localidad"])
            )
        except Exception as error:
            resultado_mapa = {
                "estado": "error",
                "mensaje": f"No fue posible completar la consulta: {error}",
                "lugares": [],
            }

    contexto_caso = f"""
Caso #{caso["id"]}
Descripción: {caso["descripcion"]}
Localidad: {caso["localidad"]}
Tipo: {caso["tipo"]}
Categoría: {caso["categoria"]}
Riesgo: {caso["nivel_riesgo"]}
Resumen: {caso["resumen"]}
Recomendaciones iniciales: {caso["recomendaciones"]}
"""

    conversacion = "\n".join(
        f"{mensaje.rol}: {mensaje.texto}"
        for mensaje in datos.historial[-8:]
    )

    if resultado_mapa is not None:
        contexto_mapa = json.dumps(
            resultado_mapa,
            ensure_ascii=False,
            indent=2,
        )
    else:
        contexto_mapa = "No se consultó el mapa para esta pregunta."

    prompt = f"""
Eres el asistente de seguimiento de BiciCerca Bogotá.
Responde en español claro, con tono amable y de forma breve.
Contesta directamente la pregunta actual usando el caso como contexto.

Reglas:
- No inventes negocios, direcciones, horarios, teléfonos, rutas ni
  condiciones actuales de las vías.
- No repitas las recomendaciones iniciales del caso si no son pertinentes
  a la pregunta actual.
- No añadas frases genéricas de seguridad que no correspondan al problema.
- Si la persona pregunta si debe seguir usando la bicicleta y reportó una
  falla mecánica, recomienda detener el uso hasta que revisen el componente
  afectado si la falla puede hacerle perder el control.
- Si se consultó el mapa, responde con una frase breve para introducir los resultados. 
  No digas que la aplicación mostrará la lista. No enumeres nombres, direcciones, 
  distancias ni enlaces; el backend añadirá una sola lista al final de tu respuesta.
- La búsqueda de lugares se basa en un punto de referencia de la localidad,
  no en la ubicación GPS exacta de la persona.
- Los lugares pueden estar relacionados con bicicletas, pero la información
  no confirma necesariamente que ofrezcan reparación.
- Si no se consultó el mapa, no menciones el mapa.
- No afirmes que la bicicleta es segura basándote solo en una descripción
  o imagen.
- No des instrucciones de reparación mecánica que requieran herramientas
  o experiencia técnica.

Información del caso:
{contexto_caso}

Resultado de la consulta del mapa:
{contexto_mapa}

Conversación reciente:
{conversacion or "No hay mensajes anteriores."}

Pregunta actual:
{datos.pregunta}
"""

    try:
        cliente = genai.Client(api_key=clave)
        respuesta = cliente.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo obtener respuesta de Gemini: {error}",
        ) from error

    texto_respuesta = respuesta.text or "No se recibió una respuesta."
    herramientas_ejecutadas = []

    if consultar_mapa and resultado_mapa is not None:
        herramientas_ejecutadas.append("Geoapify: búsqueda de lugares")

        if resultado_mapa.get("estado") == "ok":
            lugares = resultado_mapa.get("lugares", [])

            if lugares:
                # El backend agrega la lista una sola vez. Gemini no la enumera.
                texto_respuesta += crear_lista_lugares(resultado_mapa)
            else:
                texto_respuesta += (
                    "\n\nLa búsqueda no encontró lugares relacionados "
                    "con bicicletas en el área consultada."
                )
        else:
            mensaje_mapa = resultado_mapa.get(
                "mensaje",
                "No fue posible consultar el mapa.",
            )
            texto_respuesta += f"\n\nNo pude consultar el mapa: {mensaje_mapa}"

    return {
        "id_caso": id_caso,
        "respuesta": texto_respuesta,
        "herramientas_ejecutadas": herramientas_ejecutadas,
    }
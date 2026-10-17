import os
import unicodedata
from typing import List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from google import genai
from google.genai import types
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


load_dotenv()


class ResultadoClasificacion(BaseModel):
    categoria: Literal[
        "infraestructura",
        "orientacion de ruta",
        "seguridad vial",
        "consulta general",
    ]
    nivel_riesgo: Literal["bajo", "medio", "alto"]
    resumen: str
    es_suficiente: bool = Field(
        description="Indica si la información permite orientar el caso."
    )
    inconsistencias: str = Field(
        description=(
            "Diferencias entre lo que dice la persona y lo que se observa "
            "en la imagen. Deja vacío si no hay diferencia o no hay imagen."
        )
    )
    observaciones_imagen: str = Field(
        description="Describe únicamente lo que se observa en la imagen."
    )
    preguntas_aclaracion: List[str] = Field(
        description=(
            "Preguntas concretas para completar la información. "
            "No deben repetirse en las recomendaciones."
        )
    )


class EstadoAnalisis(TypedDict):
    descripcion: str
    localidad: str
    tipo: str
    imagen_bytes: Optional[bytes]
    imagen_mime: Optional[str]
    categoria: str
    nivel_riesgo: str
    resumen: str
    es_suficiente: bool
    inconsistencias: str
    observaciones_imagen: str
    preguntas_aclaracion: List[str]
    recomendaciones: List[str]
    agentes_ejecutados: List[str]


def normalizar_texto(texto: str) -> str:
    """Convierte el texto a minúsculas y elimina tildes para compararlo."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )


def agente_analista(estado: EstadoAnalisis) -> dict:
    clave = os.getenv("GEMINI_API_KEY")

    if not clave:
        raise ValueError(
            "No se encontró GEMINI_API_KEY. Revisa el archivo .env del backend."
        )

    cliente = genai.Client(api_key=clave)
    localidad = estado["localidad"] or "no especificada"
    imagen_bytes = estado.get("imagen_bytes")
    imagen_mime = estado.get("imagen_mime")

    prompt = f"""
Eres el agente analista de BiciCerca Bogotá, una aplicación de orientación
para personas que se movilizan en bicicleta.

Clasifica el caso usando únicamente estas categorías:
- infraestructura: huecos, obstáculos o daños en ciclorrutas.
- orientacion de ruta: solicitudes para orientar un recorrido.
- seguridad vial: accidentes, choques, caídas, atropellos o fallas
  que puedan poner en riesgo a la persona ciclista.
- consulta general: otras consultas relacionadas con bicicletas.

CRITERIOS DE RIESGO:
- alto: se reporta un accidente, una lesión, un atropello o un peligro
  inmediato para una persona.
- medio: se reporta una falla u obstáculo que podría afectar la seguridad.
- bajo: consulta general o solicitud de orientación sin peligro reportado.

REGLAS:
- Interpreta las negaciones correctamente. Si la persona dice “no hubo caída”
  o “nadie está lesionado”, no clasifiques esos hechos como ocurridos.
- No inventes datos, causas confirmadas, lugares, rutas ni condiciones
  actuales de las vías.
- Diferencia lo que la persona reporta de lo que se observa en la imagen.
- Describe solo elementos visibles en la imagen.
- No afirmes que una pieza funciona correctamente solo por verla.
- Si mencionas una causa no confirmada, preséntala como posibilidad.
- Si la descripción y la imagen parecen referirse a problemas distintos,
  explica esa diferencia en inconsistencias y formula una pregunta concreta.
- Una diferencia entre el relato y la imagen no debe aumentar por sí sola
  el nivel de riesgo. Evalúa el riesgo según el peligro descrito.
- La imagen es opcional. Su ausencia no es una contradicción y no debe ser,
  por sí sola, motivo para considerar insuficiente la descripción.
- Si no se adjunta imagen, deja vacíos los campos de observaciones de imagen
  e inconsistencias.
- Si falta información escrita importante, formula preguntas concretas
  en preguntas_aclaracion.
- No copies las preguntas de aclaración en el resumen ni en otro campo.
- No afirmes que registraste una acción. La aplicación informa el registro
  solo después de guardarlo en la base de datos.
- Responde en español claro y breve.

Descripción reportada: {estado["descripcion"]}
Localidad indicada: {localidad}
Tipo de caso: {estado["tipo"]}
"""

    contenidos = []

    if imagen_bytes:
        contenidos.append(
            types.Part.from_bytes(
                data=imagen_bytes,
                mime_type=imagen_mime or "image/jpeg",
            )
        )

    contenidos.append(prompt)

    respuesta = cliente.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=contenidos,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ResultadoClasificacion,
        ),
    )

    if not respuesta.text:
        raise ValueError("Gemini no devolvió un análisis.")

    resultado = ResultadoClasificacion.model_validate_json(respuesta.text)

    if imagen_bytes:
        observaciones_imagen = resultado.observaciones_imagen
        inconsistencias = resultado.inconsistencias
    else:
        observaciones_imagen = "No se adjuntó una imagen para analizar."
        inconsistencias = ""

    return {
        "categoria": resultado.categoria,
        "nivel_riesgo": resultado.nivel_riesgo,
        "resumen": resultado.resumen,
        "es_suficiente": resultado.es_suficiente,
        "inconsistencias": inconsistencias,
        "observaciones_imagen": observaciones_imagen,
        "preguntas_aclaracion": resultado.preguntas_aclaracion,
        "agentes_ejecutados": (
            estado["agentes_ejecutados"] + ["analista_gemini"]
        ),
    }


def agente_orientador(estado: EstadoAnalisis) -> dict:
    descripcion = normalizar_texto(estado["descripcion"])
    observaciones = normalizar_texto(estado["observaciones_imagen"])
    inconsistencias = normalizar_texto(estado["inconsistencias"])

    # El orientador considera tanto el relato como lo observado en la foto.
    evidencia = f"{descripcion} {observaciones} {inconsistencias}"
    nivel_riesgo = estado["nivel_riesgo"]
    categoria = estado["categoria"]

    palabras_falla = (
        "falla",
        "roto",
        "rota",
        "danado",
        "danada",
        "desprendido",
        "desprendida",
        "suelto",
        "suelta",
        "flojo",
        "floja",
        "no funciona",
        "no frena",
        "no detiene",
        "cable colgando",
        "se sale",
        "pinchada",
        "desinflada",
    )

    menciona_frenos = any(
        palabra in evidencia
        for palabra in (
            "freno",
            "frenos",
            "maneta",
            "manilla de freno",
            "palanca de freno",
        )
    )
    falla_frenos = menciona_frenos and any(
        palabra in evidencia for palabra in palabras_falla
    )

    menciona_llanta = any(
        palabra in evidencia
        for palabra in ("llanta", "neumatico", "rueda")
    )
    llanta_danada = menciona_llanta and any(
        palabra in evidencia
        for palabra in (
            "pinchada",
            "desinflada",
            "perdida de aire",
            "danada",
            "rota",
        )
    )

    cadena_afectada = "cadena" in evidencia and any(
        palabra in evidencia
        for palabra in (
            "se sale",
            "salida",
            "suelta",
            "desprendida",
            "atascada",
            "danada",
        )
    )

    direccion_afectada = any(
        palabra in evidencia
        for palabra in ("direccion", "manubrio", "manillar")
    ) and any(palabra in evidencia for palabra in palabras_falla)

    # El riesgo alto viene de la clasificación del analista. No se vuelve
    # a buscar palabras como “lesión” en bruto, porque podrían estar negadas.
    if nivel_riesgo == "alto":
        recomendaciones = [
            "Si hay una persona lesionada, solicita ayuda de emergencia.",
            "Aléjate del tránsito y busca un lugar seguro.",
        ]

    elif falla_frenos and llanta_danada and inconsistencias:
        recomendaciones = [
            "No uses la bicicleta hasta que revisen presencialmente el freno "
            "que aparece dañado. Aclara también si la llanta está pinchada."
        ]

    elif falla_frenos:
        recomendaciones = [
            "Evita usar la bicicleta hasta que una persona calificada revise "
            "el freno que aparece dañado."
        ]

    elif llanta_danada:
        recomendaciones = [
            "No continúes rodando con la llanta pinchada o desinflada. "
            "Busca asistencia en un lugar seguro."
        ]

    elif cadena_afectada:
        recomendaciones = [
            "Evita usar la bicicleta hasta que revisen la cadena y el sistema "
            "de cambios."
        ]

    elif direccion_afectada:
        recomendaciones = [
            "No uses la bicicleta hasta que revisen la dirección o el manubrio, "
            "porque afecta el control."
        ]

    elif categoria == "infraestructura":
        recomendaciones = [
            "Reduce la velocidad y mantén distancia del obstáculo.",
            "Evita maniobras bruscas y busca un lugar seguro para detenerte.",
        ]

    elif categoria == "orientacion de ruta":
        recomendaciones = [
            "Indica el punto de origen y el destino para orientar la ruta."
        ]

    elif "ruido" in evidencia or "sonido" in evidencia:
        recomendaciones = [
            "Si el ruido afecta el control o la estabilidad, detente en un "
            "lugar seguro y solicita una revisión."
        ]

    elif not estado["es_suficiente"]:
        recomendaciones = [
            "Responde las preguntas de aclaración para recibir una orientación "
            "más precisa."
        ]

    else:
        recomendaciones = [
            "Si el problema afecta el control o la seguridad, detente en un "
            "lugar seguro y solicita una revisión presencial."
        ]

    return {
        "recomendaciones": recomendaciones,
        "agentes_ejecutados": estado["agentes_ejecutados"] + ["orientador"],
    }


flujo = StateGraph(EstadoAnalisis)
flujo.add_node("analista", agente_analista)
flujo.add_node("orientador", agente_orientador)

flujo.add_edge(START, "analista")
flujo.add_edge("analista", "orientador")
flujo.add_edge("orientador", END)

grafo_analisis = flujo.compile()


def ejecutar_analisis(
    descripcion: str,
    localidad: str,
    tipo: str,
    imagen_bytes: Optional[bytes] = None,
    imagen_mime: Optional[str] = None,
) -> dict:
    estado_inicial = {
        "descripcion": descripcion,
        "localidad": localidad,
        "tipo": tipo,
        "imagen_bytes": imagen_bytes,
        "imagen_mime": imagen_mime,
        "categoria": "",
        "nivel_riesgo": "bajo",
        "resumen": "",
        "es_suficiente": True,
        "inconsistencias": "",
        "observaciones_imagen": "",
        "preguntas_aclaracion": [],
        "recomendaciones": [],
        "agentes_ejecutados": [],
    }

    return grafo_analisis.invoke(estado_inicial)
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv


load_dotenv()

URL_GEOCODIFICACION = "https://api.geoapify.com/v1/geocode/search"
URL_LUGARES = "https://api.geoapify.com/v2/places"


def _consultar_api(url: str) -> dict:
    """Consulta Geoapify y convierte su respuesta JSON en un diccionario."""
    with urlopen(url, timeout=20) as respuesta:
        contenido = respuesta.read().decode("utf-8")
        return json.loads(contenido)


def buscar_lugares_bicicleta(localidad: str, limite: int = 8) -> dict:
    """
    Busca negocios relacionados con bicicletas alrededor de una localidad
    de Bogotá. La distancia parte de un punto de referencia de la localidad.
    """
    clave = os.getenv("GEOAPIFY_API_KEY")

    if not clave:
        return {
            "estado": "sin_configurar",
            "mensaje": (
                "No se encontró GEOAPIFY_API_KEY. Revisa que esté guardada "
                "en el archivo backend/.env."
            ),
            "lugares": [],
        }

    localidad_limpia = (localidad or "").strip()

    if not localidad_limpia:
        return {
            "estado": "sin_localidad",
            "mensaje": "Indica una localidad de Bogotá para buscar lugares.",
            "lugares": [],
        }

    parametros_geocodificacion = urlencode(
        {
            "text": f"{localidad_limpia}, Bogotá, Colombia",
            "type": "locality",
            "format": "json",
            "filter": "countrycode:co",
            "limit": 5,
            "lang": "es",
            "apiKey": clave,
        }
    )

    try:
        datos_geocodificacion = _consultar_api(
            f"{URL_GEOCODIFICACION}?{parametros_geocodificacion}"
        )

        resultados_geocodificacion = datos_geocodificacion.get("results", [])

        if not resultados_geocodificacion:
            return {
                "estado": "sin_resultados",
                "mensaje": (
                    f"Geoapify no encontró la localidad «{localidad_limpia}» "
                    "en Bogotá."
                ),
                "lugares": [],
            }

        punto = resultados_geocodificacion[0]
        localidad_busqueda = localidad_limpia.casefold()

        for resultado in resultados_geocodificacion:
            texto_resultado = (
                f"{resultado.get('name', '')} "
                f"{resultado.get('formatted', '')}"
            ).casefold()

            if localidad_busqueda in texto_resultado:
                punto = resultado
                break

        latitud = punto.get("lat")
        longitud = punto.get("lon")

        if latitud is None or longitud is None:
            return {
                "estado": "error",
                "mensaje": "Geoapify no devolvió coordenadas para la localidad.",
                "lugares": [],
            }

        parametros_lugares = urlencode(
            {
                "categories": "commercial.outdoor_and_sport.bicycle",
                "filter": f"circle:{longitud},{latitud},5000",
                "bias": f"proximity:{longitud},{latitud}",
                "limit": max(1, min(limite, 20)),
                "lang": "es",
                "apiKey": clave,
            }
        )

        datos_lugares = _consultar_api(
            f"{URL_LUGARES}?{parametros_lugares}"
        )

        lugares = []

        for elemento in datos_lugares.get("features", []):
            propiedades = elemento.get("properties", {})
            lat_lugar = propiedades.get("lat")
            lon_lugar = propiedades.get("lon")

            nombre = (
                propiedades.get("name")
                or propiedades.get("address_line1")
                or "Negocio relacionado con bicicletas"
            )

            direccion = (
                propiedades.get("formatted")
                or propiedades.get("address_line2")
                or "La fuente no proporcionó una dirección."
            )

            distancia = propiedades.get("distance")

            if lat_lugar is not None and lon_lugar is not None:
                enlace_mapa = (
                    "https://www.google.com/maps/search/?api=1&query="
                    f"{lat_lugar},{lon_lugar}"
                )
            else:
                enlace_mapa = ""

            lugares.append(
                {
                    "nombre": nombre,
                    "direccion": direccion,
                    "distancia_metros": distancia,
                    "latitud": lat_lugar,
                    "longitud": lon_lugar,
                    "enlace_mapa": enlace_mapa,
                    "nota": (
                        "El resultado está clasificado como relacionado con "
                        "bicicletas; confirma directamente si ofrece reparación."
                    ),
                }
            )

        return {
            "estado": "ok",
            "localidad_consultada": localidad_limpia,
            "radio_busqueda_metros": 5000,
            "referencia": (
                "Las distancias parten de un punto de referencia de la "
                "localidad, no de la ubicación GPS exacta de la persona."
            ),
            "lugares": lugares,
            "mensaje": (
                "No se encontraron lugares relacionados con bicicletas "
                "en ese radio."
                if not lugares
                else "Búsqueda completada."
            ),
        }

    except HTTPError as error:
        return {
            "estado": "error",
            "mensaje": (
                f"Geoapify rechazó la consulta (código HTTP {error.code}). "
                "Revisa la clave y los servicios habilitados."
            ),
            "lugares": [],
        }

    except (URLError, TimeoutError):
        return {
            "estado": "error",
            "mensaje": (
                "No pude conectar con Geoapify. Revisa tu conexión a internet."
            ),
            "lugares": [],
        }

    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {
            "estado": "error",
            "mensaje": "Geoapify devolvió una respuesta que no pude procesar.",
            "lugares": [],
        }
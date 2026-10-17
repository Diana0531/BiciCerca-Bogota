import json
import sqlite3
from pathlib import Path


RUTA_BD = Path(__file__).resolve().parent.parent / "bicicerca.db"


def crear_tabla():
    with sqlite3.connect(RUTA_BD) as conexion:
        # Permite consultar las columnas por nombre, como fila["name"].
        conexion.row_factory = sqlite3.Row

        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS casos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                localidad TEXT NOT NULL,
                tipo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                nivel_riesgo TEXT NOT NULL,
                resumen TEXT NOT NULL,
                recomendaciones TEXT NOT NULL DEFAULT '[]',
                agentes_ejecutados TEXT NOT NULL DEFAULT '[]',
                es_suficiente INTEGER,
                inconsistencias TEXT NOT NULL DEFAULT '',
                observaciones_imagen TEXT NOT NULL DEFAULT '',
                preguntas_aclaracion TEXT NOT NULL DEFAULT '[]',
                accion_realizada TEXT NOT NULL DEFAULT
                    'Caso registrado y análisis guardado en la base de datos',
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Agrega las columnas nuevas si la base de datos ya existía.
        # Los casos guardados anteriormente se conservan.
        columnas_existentes = {
            fila["name"]
            for fila in conexion.execute("PRAGMA table_info(casos)").fetchall()
        }

        columnas_nuevas = {
            "es_suficiente": "INTEGER",
            "inconsistencias": "TEXT NOT NULL DEFAULT ''",
            "observaciones_imagen": "TEXT NOT NULL DEFAULT ''",
            "preguntas_aclaracion": "TEXT NOT NULL DEFAULT '[]'",
            "accion_realizada": (
                "TEXT NOT NULL DEFAULT "
                "'Caso registrado y análisis guardado en la base de datos'"
            ),
        }

        for nombre, definicion in columnas_nuevas.items():
            if nombre not in columnas_existentes:
                conexion.execute(
                    f"ALTER TABLE casos ADD COLUMN {nombre} {definicion}"
                )


def guardar_analisis(descripcion, localidad, tipo, resultado):
    es_suficiente = resultado.get("es_suficiente")

    if es_suficiente is not None:
        es_suficiente = int(bool(es_suficiente))

    recomendaciones = resultado.get("recomendaciones", [])
    agentes_ejecutados = resultado.get("agentes_ejecutados", [])
    preguntas_aclaracion = resultado.get("preguntas_aclaracion", [])

    with sqlite3.connect(RUTA_BD) as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO casos (
                descripcion,
                localidad,
                tipo,
                categoria,
                nivel_riesgo,
                resumen,
                recomendaciones,
                agentes_ejecutados,
                es_suficiente,
                inconsistencias,
                observaciones_imagen,
                preguntas_aclaracion,
                accion_realizada
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                descripcion,
                localidad,
                tipo,
                resultado["categoria"],
                resultado["nivel_riesgo"],
                resultado["resumen"],
                json.dumps(recomendaciones, ensure_ascii=False),
                json.dumps(agentes_ejecutados, ensure_ascii=False),
                es_suficiente,
                resultado.get("inconsistencias", ""),
                resultado.get("observaciones_imagen", ""),
                json.dumps(preguntas_aclaracion, ensure_ascii=False),
                resultado.get(
                    "accion_realizada",
                    "Caso registrado y análisis guardado en la base de datos",
                ),
            ),
        )

        return cursor.lastrowid


def _convertir_a_lista(valor):
    if not valor:
        return []

    try:
        resultado = json.loads(valor)
    except (TypeError, json.JSONDecodeError):
        return []

    return resultado if isinstance(resultado, list) else []


def obtener_caso(id_caso):
    with sqlite3.connect(RUTA_BD) as conexion:
        conexion.row_factory = sqlite3.Row
        fila = conexion.execute(
            "SELECT * FROM casos WHERE id = ?",
            (id_caso,),
        ).fetchone()

    if fila is None:
        return None

    caso = dict(fila)
    caso["recomendaciones"] = _convertir_a_lista(caso["recomendaciones"])
    caso["agentes_ejecutados"] = _convertir_a_lista(
        caso["agentes_ejecutados"]
    )
    caso["preguntas_aclaracion"] = _convertir_a_lista(
        caso["preguntas_aclaracion"]
    )

    if caso["es_suficiente"] is not None:
        caso["es_suficiente"] = bool(caso["es_suficiente"])

    return caso


def listar_casos():
    with sqlite3.connect(RUTA_BD) as conexion:
        conexion.row_factory = sqlite3.Row
        filas = conexion.execute(
            """
            SELECT
                id,
                descripcion,
                localidad,
                tipo,
                categoria,
                nivel_riesgo,
                creado_en
            FROM casos
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(fila) for fila in filas]
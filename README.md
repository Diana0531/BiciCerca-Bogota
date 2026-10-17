# BiciCerca Bogotá

Aplicación web de orientación inicial para personas que usan bicicleta en Bogotá. Permite registrar un caso mediante una descripción escrita y una fotografía opcional, analizarlo con inteligencia artificial y consultar lugares relacionados con bicicletas por localidad.

## Contexto

El tráfico de Bogotá lleva a muchas personas a usar la bicicleta para sus desplazamientos. Otras la utilizan para hacer ejercicio o recrearse, por ejemplo, durante la Ciclovía dominical.

Una falla mecánica, un obstáculo o una situación de riesgo pueden interrumpir un recorrido. La persona quizá no sepa cómo describir el problema o qué información necesita para buscar ayuda. BiciCerca organiza los datos del caso y ofrece una orientación inicial.

La aplicación no reemplaza la revisión de un técnico ni confirma por sí sola el estado mecánico de una bicicleta.

## Usuarios

- Personas que utilizan la bicicleta para movilizarse por Bogotá.
- Personas que montan bicicleta por deporte o recreación.

## Funcionalidades implementadas

- Registro de un caso con descripción, localidad y tipo de consulta.
- Carga opcional de imágenes JPG, PNG o WebP de máximo 8 MB.
- Análisis del texto y la imagen mediante Gemini.
- Clasificación del caso, nivel de riesgo y resumen estructurado.
- Identificación de información insuficiente y generación de preguntas de aclaración.
- Consulta contextual sobre un caso mediante un chat.
- Búsqueda de lugares relacionados con bicicletas mediante Geoapify cuando la persona los solicita.
- Enlaces a Google Maps para consultar la ubicación de los lugares encontrados.
- Registro de casos y resultados en una base de datos SQLite.
- Trazabilidad de los agentes que participaron en el análisis.

## Arquitectura implementada

1. **Interfaz web — React:** presenta el formulario, permite adjuntar una imagen y muestra el análisis y el chat.
2. **Backend — FastAPI:** valida las solicitudes, coordina el procesamiento y expone la API.
3. **Modelo de IA — Gemini:** analiza la descripción y, si se adjunta, la imagen. Devuelve una clasificación estructurada en español.
4. **Orquestación — LangGraph:** ejecuta los agentes del análisis en una secuencia definida.
5. **Agente analista:** clasifica el caso, estima el nivel de riesgo, revisa la imagen y señala preguntas o inconsistencias.
6. **Agente orientador:** prepara recomendaciones según la categoría, el riesgo y la información disponible.
7. **Datos propios — SQLite:** guarda los casos, los resultados y los agentes que participaron. El backend recupera el caso guardado para dar contexto al chat.
8. **Servicio externo — Geoapify:** busca lugares relacionados con bicicletas en la localidad indicada. El backend incorpora los resultados a la respuesta cuando detecta una solicitud para buscar lugares.

### Flujo general

La persona registra un caso en la interfaz. FastAPI recibe la descripción y la imagen opcional. LangGraph coordina al analista y al orientador. El resultado se guarda en SQLite y se muestra en la interfaz.

En el chat, el backend recupera la información del caso para responder con contexto. Si la persona solicita buscar lugares relacionados con bicicletas, el backend consulta Geoapify y agrega los resultados a la respuesta.

## Tecnologías y servicios

- **Frontend:** React, Vite y JavaScript.
- **Backend:** Python y FastAPI.
- **Inteligencia artificial:** Gemini (`gemini-3.5-flash-lite`).
- **Agentes y orquestación:** LangGraph.
- **Validación de datos:** Pydantic.
- **Base de datos:** SQLite.
- **Geolocalización y búsqueda de lugares:** Geoapify.
- **Mapas:** enlaces de consulta de ubicación en Google Maps.

## Datos, herramientas y acciones

### Datos propios

SQLite conserva los casos registrados y sus resultados. El backend puede recuperar un caso para usarlo como contexto durante el chat.

### Herramientas

- **Consulta de caso:** recuperación de información propia mediante SQLite.
- **Búsqueda de lugares:** consulta del servicio Geoapify cuando la persona pide lugares relacionados con bicicletas.

### Acción realizada

Al analizar un caso, la aplicación lo registra junto con su resultado en la base de datos SQLite.

## Alcance y limitaciones

- La búsqueda de lugares utiliza la localidad del caso y un punto de referencia. No utiliza la ubicación GPS exacta de la persona.
- La aplicación busca lugares relacionados con bicicletas; los datos consultados no siempre confirman que ofrezcan reparación.
- La versión actual no calcula rutas para llegar a los lugares.
- El análisis de una imagen no confirma que una bicicleta sea segura ni reemplaza una inspección presencial.
- El chat utiliza el caso y el historial reciente que recibe desde la interfaz. El historial del chat no se conserva en SQLite.
- La aplicación ofrece orientación inicial; no realiza reparaciones ni confirma diagnósticos mecánicos.

## Requisitos para ejecutar el proyecto

- Python 3.12.
- Node.js y npm.
- Una clave de API de Gemini.
- Una clave de API de Geoapify.

## Configuración

1. Clona o descarga el repositorio.
2. En la carpeta principal, revisa el archivo `env.example`.
3. Crea `backend/.env` con las variables requeridas. Escribe allí tus claves reales, pero no las publiques en GitHub.

Ejemplo para `backend/.env`:

```env
GEMINI_API_KEY=tu_clave_de_gemini
GEOAPIFY_API_KEY=tu_clave_de_geoapify
```

4. Instala las dependencias del backend desde PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

5. Inicia el backend:

```powershell
python -m uvicorn app.main:app --reload
```

La API estará disponible en `http://127.0.0.1:8000`. La documentación interactiva de FastAPI estará en `http://127.0.0.1:8000/docs`.

6. Abre otra terminal de PowerShell e inicia el frontend:

```powershell
cd frontend
npm install
npm run dev
```

Abre en el navegador la dirección que indique Vite, normalmente `http://localhost:5173`.

## Endpoints principales

| Método | Ruta | Función |
|---|---|---|
| `GET` | `/` | Verifica el mensaje inicial de la API. |
| `GET` | `/salud` | Comprueba el estado del backend. |
| `POST` | `/casos/analizar` | Analiza y guarda un caso. |
| `GET` | `/casos` | Consulta los casos registrados. |
| `GET` | `/casos/{id_caso}` | Recupera un caso por su identificador. |
| `POST` | `/casos/{id_caso}/chat` | Envía una pregunta contextual sobre un caso. |

## Seguridad de las claves

No publiques el archivo `backend/.env` ni incluyas claves reales en `env.example`. El archivo de ejemplo debe contener nombres de variables y valores ficticios.
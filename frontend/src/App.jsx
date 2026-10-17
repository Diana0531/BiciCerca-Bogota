import { useEffect, useRef, useState } from "react";
import "./App.css";

const URL_BACKEND = "http://127.0.0.1:8000";
const MAXIMO_IMAGEN = 8 * 1024 * 1024;

function renderizarTextoChat(texto) {
  const textoLimpio = String(texto || "")
    .replace(/\*\*(.*?)\*\*/gs, "$1")
    .replace(
      /\[([^\]]+)\]\((?:\[)?(https?:\/\/[^\s)\]]+)(?:\]\(https?:\/\/[^\s)]+\))?\)?\)/g,
      "$1: $2"
    );

  const partes = textoLimpio.split(/(https?:\/\/[^\s)\]]+)/g);

  return partes.map((parte, indice) => {
    if (/^https?:\/\//i.test(parte)) {
      return (
        <a
          key={indice}
          href={parte}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: "#176b48",
            textDecoration: "underline",
            overflowWrap: "anywhere",
          }}
        >
          Abrir ubicación en el mapa
        </a>
      );
    }

    return parte;
  });
}

function IlustracionBicicleta() {
  return (
    <svg
      className="bike-illustration"
      viewBox="0 0 560 360"
      role="img"
      aria-label="Ilustración de una persona recorriendo Bogotá en bicicleta"
    >
      <circle cx="438" cy="78" r="42" fill="#f5c86a" />
      <path
        d="M0 235 Q90 155 180 225 T360 205 T560 220 V360 H0Z"
        fill="#c8e9d2"
      />
      <path
        d="M0 280 Q110 215 220 270 T430 250 T560 270 V360 H0Z"
        fill="#a9d9bb"
      />
      <g className="city">
        <path d="M42 218V154H91V218M54 154V132H80V154" />
        <path d="M102 218V176H147V218M112 176V151H137V176" />
        <path d="M413 210V145H464V210M426 145V119H451V145" />
        <path d="M474 215V169H520V215M483 169V147H511V169" />
      </g>
      <path
        d="M0 315 Q130 280 280 312 T560 305"
        fill="none"
        stroke="#f7fbf8"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray="2 18"
      />
      <g className="bike-wheels">
        <circle cx="155" cy="265" r="58" />
        <circle cx="408" cy="265" r="58" />
      </g>
      <g className="bike-frame">
        <path d="M155 265L255 265L215 177L155 265Z" />
        <path d="M215 177L330 177L255 265" />
        <path d="M330 177L408 265" />
        <path d="M330 177L350 145L378 145" />
        <path d="M215 177L198 151L170 151" />
        <path d="M255 265L274 244" />
        <circle cx="255" cy="265" r="10" />
      </g>
      <g className="cyclist">
        <circle cx="265" cy="88" r="22" fill="#eaa276" />
        <path
          d="M243 84Q246 57 273 63Q288 67 287 86Q271 77 243 84Z"
          fill="#254d3e"
        />
        <path
          d="M250 116Q270 106 291 120L329 164L302 183L269 151L239 178L215 166Z"
          fill="#f8fbf8"
        />
        <path d="M251 119L216 165L196 152" />
        <path d="M290 122L333 158L352 145" />
        <path d="M270 151L301 207L257 260" />
        <path d="M301 207L336 239L315 254" />
        <path d="M239 176L229 225L268 253" />
        <path d="M229 225L204 251L218 264" />
      </g>
    </svg>
  );
}

function App() {
  const [formulario, setFormulario] = useState({
    descripcion: "",
    localidad: "",
    tipo: "consulta",
  });

  const [imagen, setImagen] = useState(null);
  const [vistaPrevia, setVistaPrevia] = useState("");
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  const [pregunta, setPregunta] = useState("");
  const [mensajes, setMensajes] = useState([]);
  const [enviandoMensaje, setEnviandoMensaje] = useState(false);

  const selectorImagen = useRef(null);
  const finalChat = useRef(null);

  useEffect(() => {
    if (!vistaPrevia) return undefined;
    return () => URL.revokeObjectURL(vistaPrevia);
  }, [vistaPrevia]);

  useEffect(() => {
    finalChat.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes]);

  function actualizarCampo(evento) {
    const { name, value } = evento.target;
    setFormulario((actual) => ({ ...actual, [name]: value }));
  }

  function seleccionarImagen(archivo) {
    if (!archivo) return;

    const tiposPermitidos = ["image/jpeg", "image/png", "image/webp"];

    if (!tiposPermitidos.includes(archivo.type)) {
      setError("Selecciona una imagen JPG, PNG o WebP.");
      return;
    }

    if (archivo.size > MAXIMO_IMAGEN) {
      setError("La imagen debe pesar máximo 8 MB.");
      return;
    }

    setError("");
    setImagen(archivo);
    setVistaPrevia(URL.createObjectURL(archivo));
  }

  async function analizarCaso(evento) {
    evento.preventDefault();
    setCargando(true);
    setError("");
    setResultado(null);
    setMensajes([]);

    try {
      const datos = new FormData();
      datos.append("descripcion", formulario.descripcion.trim());
      datos.append("localidad", formulario.localidad.trim());
      datos.append("tipo", formulario.tipo);

      if (imagen) {
        datos.append("imagen", imagen);
      }

      const respuesta = await fetch(`${URL_BACKEND}/casos/analizar`, {
        method: "POST",
        body: datos,
      });

      const datosRespuesta = await respuesta.json();

      if (!respuesta.ok) {
        throw new Error(datosRespuesta.detail || "No se pudo analizar el caso.");
      }

      setResultado(datosRespuesta);
    } catch (problema) {
      setError(
        problema.message ||
          "No fue posible conectar con el backend. Verifica que siga abierto."
      );
    } finally {
      setCargando(false);
    }
  }

  async function enviarPregunta(evento) {
    evento.preventDefault();

    const preguntaActual = pregunta.trim();
    if (!preguntaActual || !resultado?.id_caso || enviandoMensaje) return;

    const historialAnterior = mensajes.map((mensaje) => ({
      rol: mensaje.rol,
      texto: mensaje.texto,
    }));

    setMensajes((actuales) => [
      ...actuales,
      { rol: "usuario", texto: preguntaActual },
    ]);
    setPregunta("");
    setEnviandoMensaje(true);

    try {
      const respuesta = await fetch(
        `${URL_BACKEND}/casos/${resultado.id_caso}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pregunta: preguntaActual,
            historial: historialAnterior,
          }),
        }
      );

      const datos = await respuesta.json();

      if (!respuesta.ok) {
        throw new Error(datos.detail || "No se pudo responder la pregunta.");
      }

      setMensajes((actuales) => [
        ...actuales,
        { rol: "asistente", texto: datos.respuesta },
      ]);
    } catch (problema) {
      setMensajes((actuales) => [
        ...actuales,
        {
          rol: "asistente",
          texto: `No pude responder en este momento: ${problema.message}`,
        },
      ]);
    } finally {
      setEnviandoMensaje(false);
    }
  }

  function limpiarFormulario() {
    setFormulario({
      descripcion: "",
      localidad: "",
      tipo: "consulta",
    });
    setImagen(null);
    setVistaPrevia("");
    setResultado(null);
    setError("");
    setPregunta("");
    setMensajes([]);

    if (selectorImagen.current) {
      selectorImagen.current.value = "";
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-icon" aria-hidden="true">
            🚲
          </span>
          <span className="brand-name">
            <strong>BiciCerca</strong>
            <small>Bogotá</small>
          </span>
        </a>

        <div className="location-label">
          <span className="status-dot" />
          Asistente para ciclistas
        </div>
      </header>

      <main className="main-content">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">BOGOTÁ SE MUEVE EN BICICLETA</p>
            <h1>
              Tu camino en bici,
              <br />
              <span>más claro y seguro.</span>
            </h1>
            <p className="hero-text">
              En Bogotá, el tráfico pesado hace que muchas personas elijan la
              bicicleta para llegar más rápido. Y los domingos, la Ciclovía
              invita a salir, hacer deporte y recorrer la ciudad.
            </p>
            <a className="hero-link" href="#formulario">
              Cuéntanos qué ocurre en tu recorrido <span>→</span>
            </a>
          </div>

          <div className="hero-art">
            <div className="art-label">BOGOTÁ · CICLOVÍA · BICICLETA</div>
            <IlustracionBicicleta />
            <div className="art-caption">
              <span className="caption-icon">✦</span>
              <span>
                <strong>Cada recorrido cuenta</strong>
                <small>Muévete, disfruta y cuídate.</small>
              </span>
            </div>
          </div>
        </section>

        <section className="workspace" id="formulario">
          <form className="panel form-panel" onSubmit={analizarCaso}>
            <div className="panel-heading">
              <span className="step-number">01</span>
              <div>
                <h2>Cuéntanos tu caso</h2>
                <p>Describe la situación de tu recorrido.</p>
              </div>
            </div>

            <label htmlFor="descripcion">¿Qué está pasando?</label>
            <textarea
              id="descripcion"
              name="descripcion"
              value={formulario.descripcion}
              onChange={actualizarCampo}
              placeholder="Ejemplo: Hay un hueco grande en la ciclorruta cerca al Parque El Tunal."
              minLength={10}
              maxLength={1500}
              required
              rows={5}
            />

            <div className="field-row">
              <div className="field">
                <label htmlFor="localidad">Localidad</label>
                <input
                  id="localidad"
                  name="localidad"
                  value={formulario.localidad}
                  onChange={actualizarCampo}
                  placeholder="Ejemplo: Tunjuelito"
                  maxLength={80}
                />
              </div>

              <div className="field">
                <label htmlFor="tipo">Tipo de caso</label>
                <select
                  id="tipo"
                  name="tipo"
                  value={formulario.tipo}
                  onChange={actualizarCampo}
                >
                  <option value="consulta">Consulta</option>
                  <option value="incidente">Incidente</option>
                  <option value="ruta">Orientación de ruta</option>
                </select>
              </div>
            </div>

            <div
              style={{
                marginTop: 18,
                padding: 18,
                border: "1px dashed #9bc9aa",
                borderRadius: 14,
                background: "#f5fbf6",
              }}
            >
              <label
                htmlFor="imagen"
                style={{ display: "block", marginBottom: 8, fontWeight: 700 }}
              >
                ¿La bicicleta o la vía presenta un daño? Adjunta una foto
                <span style={{ fontWeight: 400 }}> (opcional)</span>
              </label>
              <p style={{ margin: "0 0 12px" }}>
                Gemini analizará la imagen junto con tu descripción. JPG, PNG o
                WebP de máximo 8 MB.
              </p>
              <input
                ref={selectorImagen}
                id="imagen"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(evento) =>
                  seleccionarImagen(evento.target.files?.[0])
                }
              />

              {vistaPrevia && (
                <div style={{ marginTop: 14 }}>
                  <img
                    src={vistaPrevia}
                    alt="Vista previa de la imagen seleccionada"
                    style={{
                      display: "block",
                      maxWidth: "100%",
                      maxHeight: 240,
                      borderRadius: 12,
                      objectFit: "contain",
                    }}
                  />
                  <p>Imagen seleccionada: {imagen?.name}</p>
                  <button
                    type="button"
                    onClick={() => {
                      setImagen(null);
                      setVistaPrevia("");
                      if (selectorImagen.current) {
                        selectorImagen.current.value = "";
                      }
                    }}
                  >
                    Quitar imagen
                  </button>
                </div>
              )}
            </div>

            {error && (
              <div className="error-message" role="alert">
                <h2>No se pudo completar el análisis</h2>
                <p>{error}</p>
              </div>
            )}

            <button
              className="submit-button"
              type="submit"
              disabled={cargando}
            >
              {cargando ? "Analizando caso..." : "Analizar mi caso"}
              {!cargando && <span aria-hidden="true">→</span>}
            </button>

            <p className="form-note">
              BiciCerca ofrece una orientación inicial para apoyar tu recorrido.
            </p>
          </form>

          <section className="panel result-panel" aria-live="polite">
            {!resultado && !error && !cargando && (
              <div className="empty-result">
                <span className="result-icon" aria-hidden="true">
                  🚴‍♀️
                </span>
                <p className="result-kicker">TU ORIENTACIÓN PERSONALIZADA</p>
                <h2>Estamos aquí para ayudarte</h2>
                <p>
                  Completa el formulario y Gemini analizará tu caso para darte
                  recomendaciones iniciales.
                </p>
              </div>
            )}

            {cargando && (
              <div className="loading-message">
                <span className="loading-dot" />
                Gemini está analizando tu caso...
              </div>
            )}

            {resultado && (
              <div className="analysis-result">
                <div className="panel-heading">
                  <span className="step-number">02</span>
                  <div>
                    <h2>Orientación del caso</h2>
                    <p>Caso registrado #{resultado.id_caso}</p>
                  </div>
                </div>

                <div className="result-tags">
                  <span className="tag">{resultado.categoria}</span>
                  <span className={`tag risk-${resultado.nivel_riesgo}`}>
                    Riesgo {resultado.nivel_riesgo}
                  </span>
                </div>

                <h3>Resumen</h3>
                <p className="summary-text">{resultado.resumen}</p>

                {resultado.observaciones_imagen && (
                  <>
                    <h3>Observaciones de la imagen</h3>
                    <p className="summary-text">
                      {resultado.observaciones_imagen}
                    </p>
                  </>
                )}

                {resultado.inconsistencias && (
                  <>
                    <h3>Información por aclarar</h3>
                    <p className="summary-text">{resultado.inconsistencias}</p>
                  </>
                )}

                {resultado.es_suficiente === false && (
                  <p className="summary-text">
                    La información todavía no es suficiente para orientar el
                    caso con confianza. Puedes responder las preguntas en el
                    chat de abajo.
                  </p>
                )}

                {resultado.preguntas_aclaracion?.length > 0 && (
                  <>
                    <h3>Preguntas para completar el caso</h3>
                    <ul className="recommendation-list">
                      {resultado.preguntas_aclaracion.map((texto, indice) => (
                        <li key={indice}>{texto}</li>
                      ))}
                    </ul>
                  </>
                )}

                <h3>Recomendaciones</h3>
                <ul className="recommendation-list">
                  {resultado.recomendaciones?.map((texto, indice) => (
                    <li key={indice}>{texto}</li>
                  ))}
                </ul>

                <p className="agents">
                  Agentes ejecutados:{" "}
                  {resultado.agentes_ejecutados?.join(" → ")}
                </p>

                <section
                  aria-label="Chat sobre el caso"
                  style={{
                    marginTop: 24,
                    padding: 18,
                    border: "1px solid #d8e9dd",
                    borderRadius: 16,
                    background: "#fbfefb",
                  }}
                >
                  <h3 style={{ marginTop: 0 }}>Conversemos sobre tu caso</h3>
                  <p>
                    Responde las preguntas de aclaración o escribe otra duda
                    sobre este caso.
                  </p>

                  <div
                    style={{
                      maxHeight: 280,
                      overflowY: "auto",
                      display: "grid",
                      gap: 10,
                      marginBottom: 14,
                    }}
                  >
                    {mensajes.length === 0 && (
                      <p style={{ color: "#66766d" }}>
                        Por ejemplo: “No hubo personas lesionadas” o “¿Qué debo
                        hacer antes de llevarla al taller?”
                      </p>
                    )}

                    {mensajes.map((mensaje, indice) => (
                      <div
                        key={indice}
                        style={{
                          justifySelf:
                            mensaje.rol === "usuario" ? "end" : "start",
                          maxWidth: "90%",
                          padding: "10px 14px",
                          borderRadius: 14,
                          background:
                            mensaje.rol === "usuario" ? "#e1f2e7" : "#f0f4f1",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        <strong>
                          {mensaje.rol === "usuario" ? "Tú" : "BiciCerca"}:
                        </strong>{" "}
                        {renderizarTextoChat(mensaje.texto)}
                      </div>
                    ))}

                    {enviandoMensaje && (
                      <p aria-live="polite">Gemini está respondiendo…</p>
                    )}
                    <div ref={finalChat} />
                  </div>

                  <form
                    onSubmit={enviarPregunta}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "minmax(0, 1fr) auto",
                      alignItems: "stretch",
                      gap: 8,
                      width: "100%",
                    }}
                  >
                    <input
                      type="text"
                      value={pregunta}
                      onChange={(evento) => setPregunta(evento.target.value)}
                      placeholder="Escribe tu respuesta o pregunta…"
                      maxLength={1000}
                      required
                      style={{
                        boxSizing: "border-box",
                        width: "100%",
                        minWidth: 0,
                        height: 48,
                        padding: "0 12px",
                        border: "1px solid #cfded2",
                        borderRadius: 10,
                        fontSize: 14,
                      }}
                    />
                    <button
                      type="submit"
                      disabled={enviandoMensaje || !pregunta.trim()}
                      style={{
                        width: "auto",
                        minWidth: 100,
                        flex: "none",
                        padding: "0 18px",
                        whiteSpace: "nowrap",
                      }}
                      className="submit-button"
                    >
                      Enviar
                    </button>
                  </form>
                </section>

                <button
                  className="submit-button"
                  type="button"
                  onClick={limpiarFormulario}
                  style={{ marginTop: 18 }}
                >
                  Crear otro caso
                </button>
              </div>
            )}
          </section>
        </section>

        <footer className="page-footer">
          <span>🚲</span>
          BiciCerca Bogotá · Una propuesta para acompañar la movilidad en bici
        </footer>
      </main>
    </div>
  );
}

export default App;
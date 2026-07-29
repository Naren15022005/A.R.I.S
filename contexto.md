# ARIS — Artificial Reasoning Intelligent System

> Versión: 0.7.0 · Núcleo: simbólico puro (sin LLM)
> Estado: Fases 0-3 + 5-7 + 9 + 10 completas · Cerebro Vivo (Red Neuro-Simbólica)

---

## ¿Qué es ARIS?

ARIS es una **arquitectura cognitiva simbólica** (estilo SOAR/ACT-R, sistemas expertos). No usa un LLM en el núcleo para tomar decisiones — piensa con hechos, reglas condición→acción, un motor de inferencia que decide por matching y priorización, un motor de inducción que genera reglas nuevas detectando patrones, y un **Grafo Tipado Vivo** con plasticidad hebbiana.

Stack: **Python 3.14+** · **stdlib** (`sqlite3`, `json`, `ast`, `subprocess`, `urllib`, `importlib`) · 0 dependencias externas en el núcleo.
FastAPI + uvicorn como capa API opcional. Dependencias opcionales (Ollama, sentence-transformers, BCI/PennyLane) integradas como módulos de percepción y herramientas sin tocar la naturaleza determinista del núcleo.

---

## Las 5 piezas del núcleo + Red Neuro-Simbólica

| Pieza | Archivo | Responsabilidad |
|---|---|---|
| Base de Conocimiento | `aris/conocimiento.py` | Hechos: `(sujeto, predicado, objeto)` en SQLite |
| Base de Reglas | `aris/reglas.py` | Reglas condición→acción con prioridad y contadores |
| Memoria de Trabajo | `aris/memoria.py` | Estado de sesión en RAM + persistencia SQLite |
| Motor de Inferencia | `aris/reglas.py` (MotorInferencia) | Matching input↔reglas, priorización, ejecución |
| Motor de Inducción | `aris/induccion.py` | Detecta patrones y generaliza reglas nuevas |
| GrafoConocimiento | `aris/grafo.py` | Grafo tipado vivo (nodos morados/teal/dorado/esmeralda, aristas manual/semántica/inferida) |
| RegistroPercepcion | `aris/percepcion/` | Percepción multicanal (SLM, expresiones regulares, señales BCI) |
| MotorEmbeddings | `aris/embeddings.py` | Vectores semánticos y similitud coseno (fallback Jaccard) |
| BusEventos & WebSocket | `aris/eventos.py` | Pub/Sub en memoria y streaming en tiempo real vía `/ws/grafo` |

**Principio Rector:** Nada externo decide dentro del ciclo. Todo entra como **percepción** (se traduce a hechos), **herramienta** (ejecuta y devuelve un resultado) o **memoria** (se guarda y conecta). El motor simbólico sigue siendo el único que toma decisiones.

---

## El ciclo `loopy` (Flujo Actual del Sistema v0.7.0)

```
Usuario → Entrada (texto libre, comando directo o señal BCI)
  ↓
  1. Percepción Multicanal (RegistroPercepcion):
     - CanalTextoSLM: Ollama local (Phi-4) o fallback a patrones deterministas.
     - CanalBCI: Mapeo de lecturas biométricas a hechos de estado de foco.
     → Produce {intención, sujeto, predicado, objeto, comando_normalizado}.
  ↓
  2. Actualizar MemoriaTrabajo & Registrar Nodo de Percepción en GrafoConocimiento.
  ↓
  3. MotorInferencia: Buscar coincidencias en BaseReglas.
  ↓
  4. Priorización por PerfilRazonamiento (bonificaciones, penalizaciones).
  ↓
  5. Ejecutar Acción (GestorAcciones / FileSystemTool / TerminalTool / WebTool / QuantumTool / Habilidad).
  ↓
  6. Reflejo en Memoria:
     - Guardar Hecho en BaseConocimiento + Nodo Teal en Grafo.
     - Registrar Caso en MemoriaCasos + Nodo Dorado en Grafo.
  ↓
  7. Plasticidad & Grafo Vivo:
     - Descubrimiento de aristas `semantica` vía MotorEmbeddings.
     - Refuerzo Hebbiano (`reforzar_arista`) en aristas activadas.
     - Decaimiento gradual (`decaer_pesos`) en aristas inactivas.
  ↓
  8. MotorInduccion: Sintetizar reglas nuevas tras detectar patrones en casos.
  ↓
  9. Notificación en Tiempo Real:
     - Publicar evento en BusEventos → Transmitir vía WebSocket (/ws/grafo) al Frontend.
  ↓
  10. Retornar Respuesta al Usuario.
```

---

## ¿Qué se puede hacer hoy en ARIS?

1. **Interacción en Lenguaje Natural Libre**:
   - Hablarle a ARIS sin necesidad de aprender sintaxis estricta gracias a la `CapaPercepcion` (SLM local u offline-first regex).
2. **Consultar y Enseñar Conocimiento**:
   - `recuerda que el Sol es una estrella` → ARIS almacena el hecho en SQLite y crea un nodo de memoria en el grafo.
   - `qué sabes del Sol` → Consulta simbólica determinista.
3. **Visualización en Tiempo Real ("Galaxia ARIS")**:
   - Abrir la interfaz web (`http://localhost:8000`) y ver el grafo interactivo (nodos orbitando y aristas naciendo/reforzándose en vivo vía WebSockets).
4. **Ejecutar Herramientas en Sandbox Seguro**:
   - Manipular archivos (`lee`, `escribe`, `lista`, `borra`) dentro del área de trabajo.
   - Ejecutar comandos de sistema en lista blanca.
   - Consultar páginas web externas (`web_get`).
   - Realizar simulaciones de optimización combinatoria cuántica (`QuantumTool`).
5. **Síntesis de Habilidades (Código Automático)**:
   - Pedir a ARIS que cree nuevas herramientas en Python (`crea una herramienta que...`) y ejecutarlas tras aprobación humana.
6. **Simular Entradas Biométricas (BCI)**:
   - Pasar señales biométricas (ej. nivel de atención/foco) y ver cómo el sistema ajusta su comportamiento según el estado biológico del usuario.
7. **Monitorear Métricas de Aprendizaje**:
   - Consultar `GET /metricas/aprendizaje` para obtener la serie temporal de nodos, aristas por tipo, peso promedio y reglas inducidas.

---

## ¿Qué se ha implementado hasta ahora?

| Fase | Descripción | Estado | Tests |
|---|---|---|---|
| **Fase 0** | Núcleo simbólico mínimo (BaseConocimiento, BaseReglas, MemoriaTrabajo, MotorInferencia, Loopy, CLI) | ✅ Completada | 31 |
| **Fase 1** | Perfil de Razonamiento (Personalidad, ponderación de acciones) | ✅ Completada | +8 |
| **Fase 2** | Memoria de Casos (Episódica con similitud Jaccard) | ✅ Completada | +8 |
| **Fase 3** | Motor de Inducción (Aprendizaje automático de reglas por patrones) | ✅ Completada | +7 |
| **Fase 5** | Infraestructura API FastAPI + Docker & Docker Compose | ✅ Completada | +12 |
| **Fase 6** | Herramientas & Sandboxing (FileSystemTool, TerminalTool, WebTool) | ✅ Completada | +29 |
| **Fase 7** | Generador de Habilidades (Síntesis de código Python + Aprobación) | ✅ Completada | +22 |
| **Fase 8** | Interfaz de Voz (STT/TTS) | 🔲 Pendiente | — |
| **Fase 9** | Calidad, Cobertura de Edges & CI/CD GitHub Actions | ✅ Completada | +60 |
| **Fase 10**| **Cerebro Vivo (Red Neuro-Simbólica)**: Grafo Tipado (`aris/grafo.py`), Percepción Multicanal (`aris/percepcion/`), Embeddings (`aris/embeddings.py`), EventBus WebSocket (`aris/eventos.py`, `/ws/grafo`), QuantumTool & Refuerzo Hebbiano | ✅ Completada | +49 |
| **Total** | Suite Completa de Pruebas Unitarias e Integración | **226 / 226 PASAN** | **226** |

---

## ¿Qué falta por implementarse?

1. **Fase 8 — Interfaz de Voz (STT / TTS)**:
   - Módulo de Whisper / Vosk local para reconocimiento de voz en tiempo real y TTS offline (Piper / Coqui TTS).
2. **Integración BCI con Hardware Real (Producción)**:
   - Conexión del servidor MCP nativo de Neurosity Crown / OpenBCI + BrainFlow para reemplazar la simulación de `CanalBCI`.
3. **Backend Cuántico en la Nube**:
   - Conexión opcional de `QuantumTool` con hardware cuántico real en la nube (IBM Quantum / Braket) mediante credenciales de usuario.

---

## Cómo ejecutar

```bash
# Modo CLI interactivo:
python3 -m aris.main

# Comando directo:
python3 -m aris.main "recuerda que Mercurio es un planeta"

# Servidor API & Interfaz Web (Galaxia ARIS):
pip install -r requirements.txt
python3 -m aris.main --serve --port 8000

# Docker Compose:
docker compose up --build
```

---

## Estructura del Proyecto

```
ARIS/
├── ROADMAP.md                  # Plan de fases 0-10
├── FASE10_CEREBRO_VIVO.md      # Especificación técnica detallada de Fase 10
├── contexto.md                 # Contexto y arquitectura completa (este archivo)
├── README.md                   # Resumen ejecutivo para GitHub
├── perfil_razonamiento.json    # Perfil por defecto
├── requirements.txt            # Dependencias opcionales
├── Dockerfile
├── docker-compose.yml
├── static/
│   └── index.html              # Frontend Galaxia ARIS (Canvas + WebSocket)
├── aris/
│   ├── __init__.py             # v0.7.0
│   ├── config.py               # Rutas de base de datos y workspace
│   ├── sandbox.py              # Validación de rutas y comandos
│   ├── tools.py                # FileSystemTool, TerminalTool, WebTool, QuantumTool
│   ├── habilidades.py          # GeneradorHabilidades + RegistroHabilidades
│   ├── conocimiento.py         # BaseConocimiento (SQLite triples)
│   ├── memoria.py              # MemoriaTrabajo
│   ├── reglas.py               # EvaluadorCondicion + BaseReglas + MotorInferencia
│   ├── reglas_arranque.py      # Reglas bootstrap
│   ├── acciones.py             # GestorAcciones
│   ├── casos.py                # MemoriaCasos
│   ├── induccion.py            # MotorInduccion
│   ├── perfil.py               # PerfilRazonamiento
│   ├── loopy.py                # Ciclo cognitivo principal
│   ├── main.py                 # Entry point CLI/API
│   ├── api.py                  # FastAPI + WebSocket /ws/grafo + /metricas/aprendizaje
│   ├── grafo.py                # GrafoConocimiento (Nodos, aristas y plástico hebbiano)
│   ├── embeddings.py           # MotorEmbeddings (Vectorización & Coseno/Jaccard)
│   ├── eventos.py              # BusEventos (Pub/Sub en memoria)
│   └── percepcion/             # Percepción Multicanal
│       ├── __init__.py         # RegistroPercepcion
│       ├── base.py              # CanalPercepcion (interfaz)
│       ├── texto.py              # CanalTextoSLM (Ollama + Patterns)
│       └── bci.py                # CanalBCI (Señales biométricas)
├── tests/
│   ├── test_fase0.py          # Tests fases 0-3
│   ├── test_api.py            # Tests API
│   ├── test_fase6.py          # Tests herramientas & sandbox
│   ├── test_fase7.py          # Tests habilidades
│   ├── test_cobertura.py      # Tests de casos límite
│   ├── test_percepcion.py      # Tests capa percepción
│   └── test_fase10.py         # Tests Grafo, Embeddings, EventBus, BCI, Quantum & Hebbian
└── data/                      # Base de datos SQLite + Workspace (gitignorado)
```

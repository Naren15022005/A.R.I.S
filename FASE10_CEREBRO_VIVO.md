# ARIS — Fase 10: Cerebro Vivo (Red Neuro-Simbólica)

**Versión:** 0.7.0  
**Estado:** Completada (Fases 10.1 - 10.6)  
**Filosofía:** El núcleo simbólico (`MotorInferencia`) sigue siendo el único que decide con 100% de determinismo. Todas las adiciones de la Fase 10 (SLM, BCI, embeddings, cuántica) actúan como canales de percepción, memoria estructurada o herramientas sin alterar la naturaleza simbólica central.

---

## 🏗️ Arquitectura de las 6 Sub-Fases

### 10.1 — Modelo de Grafo Tipado (`aris/grafo.py`)
Reemplaza/complementa la representación de hechos con un grafo explícito y tipado en SQLite:
- **Tabla `nodos`**: `id`, `tipo` (`simbolico`, `percepcion`, `memoria`), `subtipo` (`regla`, `hecho`, `caso`, `canal_texto`, `canal_bci`), `etiqueta`, `metadata`.
- **Tabla `aristas`**: `id`, `origen_id`, `destino_id`, `tipo` (`manual`, `semantica`, `inferida`), `peso`.
- **Clase `GrafoConocimiento`**: `crear_nodo()`, `crear_arista()`, `nodos_por_tipo()`, `vecinos()`, `exportar_json()`.

### 10.2 — Percepción Multicanal (`aris/percepcion/`)
Estructuración de entradas mediante una arquitectura multicanal:
- **`CanalPercepcion`** (`base.py`): Interfaz común.
- **`CanalTextoSLM`** (`texto.py`): Usa Ollama local (Phi-4/Gemma) si está disponible; de lo contrario, aplica fallback a patrones por expresiones regulares.
- **`CanalBCI`** (`bci.py`): Procesa o simula señales biométricas (NeuroSky / Neurosity Crown / OpenBCI) traduciéndolas a hechos de estado de foco (`{intencion: "estado_biometrico", sujeto: "usuario", predicado: "estado_foco", objeto: "alto|medio|bajo"}`).
- **`RegistroPercepcion`** (`__init__.py`): Administrador multicanal con selección dinámica de canal.

### 10.3 — Embeddings Semánticos (`aris/embeddings.py`)
- **`MotorEmbeddings`**: Vectoriza texto vía `sentence-transformers` u Ollama embeddings endpoint, calculando similitud del coseno entre nodos.
- Generación automática de aristas `semantica` cuando la similitud supera el umbral del perfil (ej. 0.82).
- Fallback determinista a similitud Jaccard si no hay librerías de ML instaladas.

### 10.4 — Endpoint Vivo WebSocket & EventBus (`aris/eventos.py` & `aris/api.py`)
- **`BusEventos`** (`eventos.py`): Bus de eventos Pub/Sub en memoria con `asyncio` y callbacks.
- **WebSocket `@app.websocket("/ws/grafo")`**: Transmite en vivo eventos `nuevo_nodo`, `nueva_arista`, `arista_reforzada` y `decaimiento_pesos`.
- **Frontend Galaxia ARIS** (`static/index.html`): Motor Force-Directed Graph animado en HTML5 Canvas conectado por WebSocket.

### 10.5 — Herramientas Externas (`QuantumTool` en `aris/tools.py`)
- **`QuantumTool`**: Ejecuta simulaciones de recocido cuántico y QAOA acotadas a un máximo de 16 qubits/variables dentro del sandbox.

### 10.6 — Refuerzo Hebbiano & Demostración de Aprendizaje (`aris/grafo.py` & `/metricas/aprendizaje`)
- **Refuerzo Hebbiano (`reforzar_arista`)**: Incrementa el peso de una arista cuando es activada por el motor de inferencia.
- **Decaimiento Gradual (`decaer_pesos`)**: Aplica factor de decaimiento (ej. 0.98) a aristas inactivas y elimina las sub-umbral (< 0.05).
- **Endpoint `GET /metricas/aprendizaje`**: Expone métricas cuantitativas en tiempo real (nodos totales, aristas por tipo, peso promedio y reglas inducidas).

---

## 🧪 Verificación & Suite de Pruebas

Toda la funcionalidad está cubierta por la suite de pruebas:
- `tests/test_fase10.py`
- `tests/test_percepcion.py`
- `tests/test_public_framework.py`

Comando de verificación completa:
```bash
python -m pytest tests/ -v
```

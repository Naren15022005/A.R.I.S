# ARIS — Artificial Reasoning Intelligent System

> **Versión 0.7.0** · Arquitectura cognitiva simbólica (estilo SOAR/ACT-R, sistemas expertos).
> Sin LLM en el núcleo: piensa con **hechos + reglas + inferencia + inducción + grafo vivo + herramientas + habilidades**.

Stack: **Python 3.14+** · **stdlib** (`sqlite3`, `json`, `ast`, `subprocess`, `importlib`) · 0 dependencias externas en el núcleo.  
API en FastAPI, interfaz web en HTML5 Canvas con WebSockets y módulos opcionales de Percepción (Ollama / BCI), Embeddings y Optimización Cuántica (`QuantumTool`).

---

## ⚡ Inicio Rápido

```bash
# 1. Modo interactivo (CLI):
python3 -m aris.main

# 2. Comando directo en lenguaje natural:
python3 -m aris.main "recuerda que el Sol es una estrella"

# 3. Servidor API & Interfaz Web ("Galaxia ARIS"):
pip install -r requirements.txt
python3 -m aris.main --serve --port 8000
# Abre http://localhost:8000 en tu navegador
```

---

## 🚀 ¿Qué se puede hacer hoy?

- **💬 Percepción Multicanal**: Entrada en lenguaje natural libre (vía Ollama SLM o patrones deterministas *offline-first*) o señales biométricas (BCI).
- **🧠 Razonamiento Determinista**: Almacenar y consultar conocimiento mediante triples `(sujeto, predicado, objeto)` y motor de inferencia por reglas.
- **🌌 Galaxia ARIS (Grafo Vivo en Tiempo Real)**: Visualizar el mapa interactivo de nodos y aristas (reglas moradas, hechos teal, casos dorados y habilidades esmeralda) animados por WebSockets (`/ws/grafo`).
- **📈 Plasticidad y Aprendizaje Hebbiano**: Refuerzo automático de aristas utilizadas por el razonamiento y decaimiento gradual de conexiones inactivas.
- **🛠️ Sandbox y Herramientas de Sistema**: Manipular archivos, ejecutar comandos en lista blanca, explorar la web (`WebTool`) y simular recocido cuántico (`QuantumTool`).
- **⚡ Síntesis de Habilidades**: ARIS puede generar nuevas herramientas en Python desde una descripción en lenguaje natural y ejecutarlas tras aprobación humana.

---

## 📊 Estado del Proyecto

| Fase | Descripción | Estado | Tests |
|---|---|---|---|
| **Fase 0** | Núcleo simbólico mínimo (Triples, Reglas, Inferencia, Loopy) | ✅ Completada | 31 |
| **Fase 1** | Perfil de Razonamiento (Personalidad y priorización) | ✅ Completada | +8 |
| **Fase 2** | Memoria de Casos (Razonamiento basado en casos episódicos) | ✅ Completada | +8 |
| **Fase 3** | Motor de Inducción (Aprendizaje inductivo de reglas por patrones) | ✅ Completada | +7 |
| **Fase 5** | Infraestructura API FastAPI + Docker & Docker Compose | ✅ Completada | +12 |
| **Fase 6** | Herramientas en Sandbox (Archivos, Terminal, Web) | ✅ Completada | +29 |
| **Fase 7** | Generador de Habilidades (Síntesis de código Python + Aprobación) | ✅ Completada | +22 |
| **Fase 8** | Interfaz de Voz (STT/TTS) | 🔲 Pendiente | — |
| **Fase 9** | Calidad, Cobertura de Edges & CI/CD GitHub Actions | ✅ Completada | +60 |
| **Fase 10** | **Cerebro Vivo (Red Neuro-Simbólica)**: Grafo Tipado, Percepción Multicanal, Embeddings, EventBus WebSocket, QuantumTool & Plasticidad Hebbiana | ✅ Completada | +49 |
| **Total** | **Suite Completa de Pruebas Unitarias e Integración** | **226 / 226 PASAN** | **226** |

---

## 🔮 Lo que viene (Próximos Pasos)

- [ ] **Fase 8 — Interfaz de Voz (STT / TTS)**: Reconocimiento de voz local (Whisper/Vosk) y síntesis hablada offline.
- [ ] **BCI con Hardware Real**: Conexión nativa con Neurosity Crown y OpenBCI/BrainFlow.
- [ ] **Backend Cuántico en la Nube**: Conexión directa de `QuantumTool` con IBM Quantum.

---

## 📚 Documentación Técnica

- [`contexto.md`](contexto.md) — Descripción técnica completa de la arquitectura y flujo `loopy`.
- [`FASE10_CEREBRO_VIVO.md`](FASE10_CEREBRO_VIVO.md) — Plan maestro de la Red Neuro-Simbólica y el modelo de grafo.
- [`ROADMAP.md`](ROADMAP.md) — Plan detallado de fases 0 a 10.

Licencia: MIT

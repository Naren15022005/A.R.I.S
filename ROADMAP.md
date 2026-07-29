# ARIS — Roadmap: Cerebro Simbólico Autosostenible

> Núcleo: 100% simbólico, sin LLM ni redes neuronales
> LLM: módulo opcional futuro, solo para voz (STT/TTS) — nunca para decidir

---

## Filosofía

ARIS **no** usa un LLM para pensar. Piensa con:
- **Hechos** guardados y leídos por el propio sistema (memoria declarativa).
- **Reglas** condición→acción, guardadas como datos, no como funciones fijas (memoria procedimental).
- **Motor de inferencia** que hace matching entre input, hechos y reglas, y decide.
- **Motor de inducción** que genera reglas nuevas cuando detecta patrones repetidos.

**Consecuencia aceptada:** el entendimiento de lenguaje es literal al principio. Mejora con el tiempo a medida que el sistema induce más reglas de su propio uso.

**Voz (futuro):** si se añade un LLM, será exclusivamente para convertir audio↔texto en los bordes (STT/TTS) o para redactar frases más naturales de salida — nunca para decidir qué hacer.

---

## Las 5 piezas del núcleo

| Pieza | Qué guarda/hace | Analogía |
|---|---|---|
| Base de Conocimiento | Hechos: (sujeto, predicado, objeto) | "Lo que sé" |
| Base de Reglas | Condición → Acción, con prioridad y contador de éxito | "Lo que hago cuando..." |
| Memoria de Trabajo | Estado de la sesión actual (contexto inmediato) | "Lo que tengo en mente ahora" |
| Motor de Inferencia | Matching input↔reglas, prioriza, ejecuta | El razonamiento en sí |
| Motor de Inducción | Detecta patrones repetidos y genera reglas nuevas | El aprendizaje |

Todo vive dentro de `loopy`, el ciclo principal.

---

## Fases

### ✅ Fase 0 — Núcleo simbólico mínimo (walking skeleton)

- [x] `BaseConocimiento`: tabla SQLite de tripletas (sujeto, predicado, objeto, timestamp)
- [x] `BaseReglas`: tabla SQLite de reglas (condicion, accion, prioridad, exitos, fallos)
- [x] `MemoriaTrabajo`: objeto en RAM con estado de sesión (persistente al cerrar)
- [x] `MotorInferencia`: matching simple (recorrer reglas, filtrar, ordenar por prioridad — sin Rete)
- [x] `loopy`: ciclo principal, entrada/salida por consola (texto)
- [x] 10 reglas escritas a mano para arrancar
- [x] Tests (Fases 0-3): 54 tests, todos pasan

---

### ✅ Fase 1 — Perfil de razonamiento + priorización real

- [x] `PerfilRazonamiento`: archivo JSON con criterios explícitos
- [x] `MotorInferencia` usa el perfil para desempatar cuando varias reglas coinciden
- [x] Tests: dos reglas que coinciden con el mismo input, el perfil determina cuál gana

---

### ✅ Fase 2 — Memoria de casos

- [x] `MemoriaCasos`: guarda (situación, regla_aplicada, resultado, timestamp) como unidad
- [x] Búsqueda de "caso más parecido" cuando el input no matchea ninguna regla exacta (Jaccard)
- [x] Tests: input parecido a un caso anterior exitoso → reutiliza esa decisión

---

### ✅ Fase 3 — Motor de inducción (aprendizaje real)

- [x] Umbral de inducción configurable (mismo patrón → mismo resultado exitoso, N+ veces)
- [x] `MotorInduccion`: recorre memoria de casos, detecta repeticiones, genera regla nueva
- [x] Reglas inducidas se marcan con origen `inducida` (distinguibles de manuales)
- [x] Tests: forzar casos idénticos exitosos → aparece regla nueva coherente

---

### 🔳 Fase 4 — Optimización del motor de inferencia (Rete)

**Objetivo:** el sistema sigue siendo rápido con cientos de reglas.

- [ ] Medir tiempo de matching con cantidad real de reglas
- [ ] Si es necesario, indexado tipo Rete simplificado

---

### ✅ Fase 5 — Infraestructura alrededor del núcleo

- [x] FastAPI como capa de entrada/salida (además de consola)
- [x] 12 endpoints REST: chat, health, hechos CRUD, reglas CRUD, sesión
- [x] Docker + Docker Compose
- [x] Dockerfile optimizado (python:3.14-slim)
- [x] requirements.txt con dependencias opcionales
- [x] Tests: 12 tests de API, todos pasan

---

### ✅ Fase 6 — Herramientas (Tools) reales

- [x] `Sandbox`: validación de rutas, lista blanca de comandos, path traversal
- [x] `FileSystemTool`: leer/escribir/listar/eliminar archivos con sandbox
- [x] `TerminalTool`: ejecutar comandos permitidos con timeout
- [x] `WebTool`: GET a URLs con límite de tamaño
- [x] 7 acciones nuevas: `leer_archivo`, `escribir_archivo`, `listar_archivos`, `eliminar_archivo`, `ejecutar_comando`, `web_get`, `herramientas_disponibles`
- [x] 7 reglas de arranque para herramientas (prioridad 10)
- [x] Tests: 29 tests de sandbox + tools + integración

---

### ✅ Fase 7 — Generador de habilidades (síntesis de código)

- [x] `GeneradorHabilidades`: genera código Python desde descripción en lenguaje natural
- [x] `RegistroHabilidades`: guarda habilidades en `data/habilidades/<id>/` (código + metadata)
- [x] Carga dinámica con `importlib` — las habilidades aprobadas se activan sin reiniciar
- [x] Validación de sintaxis antes de registrar
- [x] Aprobación humana obligatoria (`aprueba <acción>`) antes de activar
- [x] Persistencia entre sesiones (disco + recarga al iniciar)
- [x] Soporte de "no tengo herramienta" → `ejecutar_accion` consulta el registro de habilidades
- [x] Tests: 22 tests de generación, registro, ejecución dinámica, integración con loopy

---

### 🔳 Fase 8 — Módulo de voz (LLM opcional, en el borde)

**Objetivo:** entrada/salida por voz sin tocar el núcleo de decisión.

- [ ] STT (voz→texto): el texto entra a `loopy` igual que input por consola
- [ ] TTS (texto→voz): la salida se convierte a voz sin intervenir en la decisión
- [ ] LLM aislado en este módulo — nunca decide qué acción tomar

---

### ✅ Fase 9 — Calidad y consolidación

- [x] Cobertura de tests ampliada: +60 tests de casos límite (WebTool mock, edge cases en todos los módulos, API boundary)
- [x] 3 bugs corregidos durante la auditoría (perfil JSON corrupto, código muerto en aprobar_habilidad, guardia de sesión en actualizar)
- [x] CI/CD: GitHub Actions workflow (`.github/workflows/ci.yml`)
- [x] .gitignore actualizado (data/ + .pytest_cache)
- [x] Documentación consolidada: ROADMAP.md, contexto.md, README.md sincronizados con v0.6.0
- [x] Tests: 177 tests, todos pasan

---

## Tabla resumen

| Fase | Foco | Depende de |
|---|---|---|
| 0 | Núcleo mínimo funcionando | — |
| 1 | Perfil de razonamiento | Fase 0 |
| 2 | Memoria de casos | Fase 0 |
| 3 | Inducción de reglas | Fase 1, 2 |
| 4 | Optimización (Rete) | Fase 3, cuando el volumen lo pida |
| 5 | Infraestructura (API/Docker) | Fase 0-3 validadas |
| 6 | Tools reales | Fase 5 |
| 7 | Generador de habilidades | Fase 6 |
| 8 | Voz (LLM en el borde) | Fase 0 (núcleo estable) |
| 9 ✅ | Calidad/consolidación | Todas |

---

## Riesgos aceptados

- **Rigidez inicial de lenguaje:** sin LLM, ARIS solo entiende lo que matchea con reglas conocidas. Se compensa con tiempo y uso real (Fase 3).
- **Diseño de patrones y umbrales es 100% tuyo:** la calidad depende de cómo diseñes condiciones y umbrales de inducción.
- **No optimizar antes de tiempo:** Rete (Fase 4) solo si el volumen de reglas lo exige.

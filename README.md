# ARIS — Artificial Reasoning Intelligent System

Arquitectura cognitiva simbólica (estilo SOAR/ACT-R). Sin LLM en el núcleo:
piensa con **hechos + reglas + inferencia + inducción + herramientas + habilidades**.

Stack: **Python 3.14+** · **stdlib** (sqlite3, json, ast, subprocess, importlib) · 0 dependencias externas.

## Inicio rápido

```bash
python3 -m aris.main "Hola ARIS"
python3 -m aris.main                                        # interactivo
pip install fastapi uvicorn && python3 -m aris.main --serve # API
```

## Comandos principales

```
hola / adiós / gracias / quién eres
qué sabes / reglas / ayuda
recuerda que X es Y / qué sabes de X / olvida X
lee <ruta> / escribe <ruta> con <texto> / lista <dir> / borra <ruta>
ejecuta <comando> / abre <url> / herramientas
crea una herramienta que <descripción> / aprueba <acción> / habilidades
```

## Estado

| Fase | Estado | Tests |
|---|---|---|
| 0 | ✅ Núcleo simbólico | 31 |
| 1 | ✅ Perfil de razonamiento | +8 |
| 2 | ✅ Memoria de casos | +8 |
| 3 | ✅ Inducción de reglas | +7 |
| 5 | ✅ Infraestructura API/Docker | +12 |
| 6 | ✅ Herramientas (sandbox) | +29 |
| 7 | ✅ Generador de habilidades | +22 |
| 8 | 🔲 Voz | — |
| 9 | ✅ Calidad y consolidación | +60 |
| 10 | ✅ Cerebro Vivo (Red Neuro-Simbólica) | +47 |
| **Total** | | **224 tests** |


## Documentación

- [`contexto.md`](contexto.md) — descripción técnica completa
- [`ROADMAP.md`](ROADMAP.md) — plan de fases detallado

Licencia: MIT

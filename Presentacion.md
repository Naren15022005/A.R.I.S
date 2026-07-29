# A.R.I.S
Proyecto investigacion - IA simbólica / ciencia cognitiva computacional 

ARIS es una arquitectura cognitiva simbólica (en la tradición de SOAR/ACT-R) que razona mediante hechos, reglas condición-acción y motores de inferencia e inducción — sin depender de un LLM para decidir. Su Base de Conocimiento, hoy una tabla de tripletas (sujeto-predicado-objeto), es funcionalmente un grafo de conocimiento interconectado — cada hecho es un nodo, cada relación una arista — visualizable como el "cerebro-galaxia" que diseñamos: un núcleo simbólico denso rodeado de capas de percepción y memoria. Los sentidos son módulos periféricos, nunca el núcleo: hoy es texto por consola/API; a futuro (Fase 8) será voz vía un LLM aislado en el borde (STT/TTS) que jamás toca la decisión; y el mismo patrón permitiría sumar una interfaz cerebro-computadora (EEG) como otro sentido más, alimentando loopy igual que hace hoy el texto. La computación cuántica encaja como una optimización futura y opcional del Motor de Inferencia — cuando el volumen de reglas crezca lo suficiente (tu Fase 4, hoy pensada con Rete clásico), un solver cuántico podría acelerar el matching combinatorio entre miles de reglas candidatas, sin cambiar la naturaleza simbólica y determinista del núcleo.

## Estado

v0.6.0 · Núcleo simbólico puro (sin LLM) · 177 tests

| Fase | Estado |
|---|---|
| 0-3, 5-7, 9 | ✅ Completas |
| 4 (Rete) | 🔳 Pendiente |
| 8 (Voz) | 🔳 Pendiente |

## Ejecutar

\`\`\`bash
python3 -m aris.main
\`\`\`

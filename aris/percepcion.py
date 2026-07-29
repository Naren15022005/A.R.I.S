import json
import re
import urllib.error
import urllib.request
from typing import Any

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi4"


class CapaPercepcion:
    """Capa de Percepción frontal para ARIS.
    
    Traduce entradas en lenguaje natural libre a intenciones y comandos estructurados
    sin alterar la naturaleza determinista y simbólica del núcleo cognitivo (loopy).
    """

    def __init__(self, ollama_url: str = OLLAMA_URL, model: str = OLLAMA_MODEL) -> None:
        self.ollama_url = ollama_url
        self.model = model

    def slm_disponible(self, timeout: float = 1.0) -> bool:
        """Verifica si el servicio local de SLM (Ollama) está disponible."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except Exception:
            return False

    def _via_slm(self, texto: str) -> dict[str, Any]:
        """Traduce lenguaje natural libre usando el SLM local (Ollama)."""
        prompt = (
            "Eres el módulo de percepción de ARIS (Cerebro Simbólico).\n"
            "Traduce la siguiente entrada en lenguaje natural a una intención estructurada.\n"
            "Responde ÚNICAMENTE con un objeto JSON válido con este esquema exacto:\n"
            "{\n"
            '  "intencion": "saludar" | "guardar_hecho" | "consultar_hecho" | "olvidar" | "leer_archivo" | "escribir_archivo" | "listar_archivos" | "eliminar_archivo" | "ejecutar_comando" | "web_get" | "crear_habilidad" | "desconocido",\n'
            '  "sujeto": "string o null",\n'
            '  "predicado": "string o null",\n'
            '  "objeto": "string o null",\n'
            '  "comando_normalizado": "string de comando equivalente para ARIS"\n'
            "}\n\n"
            f'Entrada del usuario: "{texto}"\n'
            "JSON:"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.ollama_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.0) as response:
                if response.status == 200:
                    resp_body = json.loads(response.read().decode("utf-8"))
                    raw_response = resp_body.get("response", "{}")
                    parsed = json.loads(raw_response)
                    if isinstance(parsed, dict) and "comando_normalizado" in parsed:
                        return parsed
        except Exception:
            pass

        return self._via_patrones(texto)

    def _via_patrones(self, texto: str) -> dict[str, Any]:
        """Fallback determinista basado en reglas y patrones literales (offline-first)."""
        lower = texto.strip().lower()

        # Saludos y cortesía
        if any(w in lower for w in ["hola", "buenas", "qué tal", "que tal"]):
            return {
                "intencion": "saludar",
                "sujeto": None,
                "predicado": None,
                "objeto": None,
                "comando_normalizado": "hola",
            }
        if any(w in lower for w in ["gracias", "graciass", "thank"]):
            return {
                "intencion": "agradecer",
                "sujeto": None,
                "predicado": None,
                "objeto": None,
                "comando_normalizado": "gracias",
            }

        # Guardar hecho: "recuerda que X es Y" o "recuerdame que X es Y" o "aprende que X es Y"
        match_rec = re.match(r"(?:recuerda(?:me)?|recuérdame|aprende)\s+que\s+(.+?)\s+(es|tiene|son)\s+(.+)", texto, re.IGNORECASE)

        if match_rec:
            suj, pred, obj = match_rec.group(1).strip(), match_rec.group(2).strip(), match_rec.group(3).strip()
            return {
                "intencion": "guardar_hecho",
                "sujeto": suj,
                "predicado": pred,
                "objeto": obj,
                "comando_normalizado": f"recuerda que {suj} {pred} {obj}",
            }

        # Consultar hecho: "qué sabes de X" / "que sabes de X"
        match_cons = re.match(r"(?:qué|que)\s+sabes\s+de\s+(.+)", texto, re.IGNORECASE)
        if match_cons:
            suj = match_cons.group(1).strip()
            return {
                "intencion": "consultar_hecho",
                "sujeto": suj,
                "predicado": None,
                "objeto": None,
                "comando_normalizado": f"qué sabes de {suj}",
            }

        # Lectura de archivos
        if lower.startswith("lee ") or lower.startswith("abre "):
            return {
                "intencion": "leer_archivo",
                "sujeto": None,
                "predicado": None,
                "objeto": None,
                "comando_normalizado": texto,
            }

        # Ejecución de comandos
        if lower.startswith("ejecuta "):
            return {
                "intencion": "ejecutar_comando",
                "sujeto": None,
                "predicado": None,
                "objeto": None,
                "comando_normalizado": texto,
            }

        return {
            "intencion": "desconocido",
            "sujeto": None,
            "predicado": None,
            "objeto": None,
            "comando_normalizado": texto,
        }

    def interpretar(self, texto: str) -> dict[str, Any]:
        """Interpreta la entrada del usuario intentando SLM local o usando patrones."""
        if self.slm_disponible():
            return self._via_slm(texto)
        return self._via_patrones(texto)

    def normalizar_comando(self, texto: str) -> str:
        """Devuelve el comando normalizado listo para ser procesado por loopy."""
        res = self.interpretar(texto)
        return res.get("comando_normalizado") or texto

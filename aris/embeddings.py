import math
import re
import urllib.request
import json
from typing import Any

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_MODEL = "nomic-embed-text"


class MotorEmbeddings:
    """Motor de Embeddings Semánticos para ARIS (Fase 10.3).
    
    Proporciona representación vectorial y métrica de similitud por coseno,
    con fallback determinista a similitud Jaccard si no hay librerías de ML instadas.
    """

    def __init__(self, ollama_url: str = OLLAMA_EMBED_URL, model: str = OLLAMA_MODEL) -> None:
        self.ollama_url = ollama_url
        self.model = model
        self._st_model = None
        self._check_sentence_transformers()

    def _check_sentence_transformers(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self._st_model = None

    def disponible(self) -> bool:
        if self._st_model is not None:
            return True
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def vectorizar(self, texto: str) -> list[float]:
        """Vectoriza un texto vía sentence-transformers, Ollama o vectorizador de tokens en stdlib."""
        if self._st_model is not None:
            return self._st_model.encode(texto).tolist()

        try:
            data = json.dumps({"model": self.model, "prompt": texto}).encode("utf-8")
            req = urllib.request.Request(self.ollama_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    res = json.loads(resp.read().decode("utf-8"))
                    if "embedding" in res:
                        return res["embedding"]
        except Exception:
            pass

        # Fallback stdlib frequency vector
        tokens = re.findall(r"\w+", texto.lower())
        if not tokens:
            return [0.0]
        # Hash fijo a 32 dimensiones
        vec = [0.0] * 32
        for t in tokens:
            idx = abs(hash(t)) % 32
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def similitud(self, a: list[float], b: list[float]) -> float:
        """Calcula la similitud del coseno entre dos vectores."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def similitud_textos(self, texto1: str, texto2: str) -> float:
        """Calcula similitud semántica. Usa cosinus de embeddings o Jaccard como fallback."""
        if self.disponible():
            v1 = self.vectorizar(texto1)
            v2 = self.vectorizar(texto2)
            return self.similitud(v1, v2)

        # Fallback Jaccard
        set1 = set(re.findall(r"\w+", texto1.lower()))
        set2 = set(re.findall(r"\w+", texto2.lower()))
        if not set1 or not set2:
            return 0.0
        inter = len(set1 & set2)
        union = len(set1 | set2)
        return inter / union if union > 0 else 0.0

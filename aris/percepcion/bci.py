from typing import Any

from aris.percepcion.base import CanalPercepcion


class CanalBCI(CanalPercepcion):
    """Canal de Percepción BCI (Brain-Computer Interface / NeuroSky / Neurosity Crown mock/real)."""

    nombre = "bci_neurosity"

    def __init__(self, hardware_sdk: Any | None = None) -> None:
        self.sdk = hardware_sdk

    def disponible(self, timeout: float = 1.0) -> bool:

        # Si hay SDK real inicializado o mock activo
        if self.sdk is not None:
            try:
                return bool(getattr(self.sdk, "is_connected", lambda: True)())
            except Exception:
                return False
        return True  # Modo simulación habilitado por defecto

    def interpretar(self, entrada: Any) -> dict[str, Any]:
        """Procesa señal BCI cruda o simulada dict/float -> hecho de estado biométrico."""
        foco_val = 0.5
        if isinstance(entrada, (int, float)):
            foco_val = float(entrada)
        elif isinstance(entrada, dict):
            foco_val = float(entrada.get("foco", entrada.get("attention", 0.5)))

        if foco_val >= 0.7:
            nivel = "alto"
        elif foco_val >= 0.4:
            nivel = "medio"
        else:
            nivel = "bajo"

        sujeto = "usuario"
        predicado = "estado_foco"
        objeto = nivel

        return {
            "intencion": "estado_biometrico",
            "sujeto": sujeto,
            "predicado": predicado,
            "objeto": objeto,
            "comando_normalizado": f"recuerda que {sujeto} {predicado} {objeto}",
        }

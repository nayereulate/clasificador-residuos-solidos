"""
Gestión de tracks con ByteTrack.
- Votación mayoritaria de clases (evita parpadeo Lata→Botella→Lata)
- Predicción de posición por inercia cuando el objeto se pierde temporalmente
- Tres estados por track: detectado / detectando / predictado
"""
import threading
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

# ── Parámetros configurables ──────────────────────────────────────────────────
HISTORY_LEN      = 24    # frames de historial de clases por track
TIMEOUT_FRAMES   = 60    # frames de inactividad antes de eliminar track
MAX_PRED_FRAMES  = 12    # máx frames a predecir sin detección (≈0.5 s a 20fps)
CLASES_ESTABLES  = 5     # frames mínimos para considerar clase "estable"
CONF_DEFAULT     = 0.05  # conf pasada al modelo (ByteTrack hace su propio filtro)
IMGSZ_DEFAULT    = 1280  # alta resolución → detecta objetos pequeños/lejanos
CAM_WIDTH        = 1280
CAM_HEIGHT       = 720

# Ruta al YAML personalizado de ByteTrack (relativa al manage.py del proyecto)
BYTETRACK_YAML = str(Path(__file__).resolve().parents[3] / "bytetrack_custom.yaml")


@dataclass
class TrackInfo:
    track_id: int

    # Historial de clasificación
    historial_clases:    deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    historial_confianza: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))

    # Posición y velocidad para predicción por inercia
    ultima_posicion: dict  = field(default_factory=dict)   # {x1,y1,x2,y2}
    prev_posicion:   dict  = field(default_factory=dict)
    velocidad:       dict  = field(default_factory=lambda: {"vx": 0.0, "vy": 0.0})

    ultimo_frame_visto:    int  = 0
    frames_sin_deteccion:  int  = 0
    contado:               bool = False

    # ── Propiedades ──────────────────────────────────────────────────────────

    @property
    def clase_dominante(self) -> str:
        if len(self.historial_clases) < 2:
            return "Detectando..."
        return Counter(self.historial_clases).most_common(1)[0][0]

    @property
    def es_clase_estable(self) -> bool:
        return len(self.historial_clases) >= CLASES_ESTABLES

    @property
    def confianza_promedio(self) -> float:
        if not self.historial_confianza:
            return 0.0
        return round(sum(self.historial_confianza) / len(self.historial_confianza), 4)

    # ── Velocidad ─────────────────────────────────────────────────────────────

    def actualizar_velocidad(self):
        if not self.prev_posicion or not self.ultima_posicion:
            return
        cx = lambda p: (p["x1"] + p["x2"]) / 2   # noqa: E731
        cy = lambda p: (p["y1"] + p["y2"]) / 2   # noqa: E731
        dx = cx(self.ultima_posicion) - cx(self.prev_posicion)
        dy = cy(self.ultima_posicion) - cy(self.prev_posicion)
        # EMA para suavizar velocidad y evitar saltos bruscos
        α = 0.35
        self.velocidad["vx"] = α * dx + (1 - α) * self.velocidad["vx"]
        self.velocidad["vy"] = α * dy + (1 - α) * self.velocidad["vy"]

    def posicion_predicha(self, steps: int = 1) -> Optional[dict]:
        """Extrapola posición usando velocidad. Retorna None si no hay posición base."""
        if not self.ultima_posicion:
            return None
        w = self.ultima_posicion["x2"] - self.ultima_posicion["x1"]
        h = self.ultima_posicion["y2"] - self.ultima_posicion["y1"]
        # Decaimiento exponencial de velocidad en predicción
        decay = 0.85 ** steps
        cx = (self.ultima_posicion["x1"] + self.ultima_posicion["x2"]) / 2
        cy = (self.ultima_posicion["y1"] + self.ultima_posicion["y2"]) / 2
        cx += self.velocidad["vx"] * decay * steps
        cy += self.velocidad["vy"] * decay * steps
        return {
            "x1": int(cx - w / 2),
            "y1": int(cy - h / 2),
            "x2": int(cx + w / 2),
            "y2": int(cy + h / 2),
        }


# ── NMS auxiliar ─────────────────────────────────────────────────────────────

def _iou(a: dict, b: dict) -> float:
    ix1 = max(a["x1"], b["x1"]); iy1 = max(a["y1"], b["y1"])
    ix2 = min(a["x2"], b["x2"]); iy2 = min(a["y2"], b["y2"])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
    ub = (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])
    return inter / (ua + ub - inter) if (ua + ub - inter) > 0 else 0.0


def _nms(detecciones: list, iou_thresh: float = 0.55) -> list:
    """
    Suprime cajas con alto solapamiento.
    Mantiene la de mayor confianza cuando dos cajas se solapan > iou_thresh.
    """
    if len(detecciones) <= 1:
        return detecciones
    ordered = sorted(detecciones, key=lambda d: d.get("confianza", 0), reverse=True)
    keep, suprimidos = [], set()
    for i, det in enumerate(ordered):
        if i in suprimidos:
            continue
        keep.append(det)
        for j in range(i + 1, len(ordered)):
            if j not in suprimidos and _iou(det, ordered[j]) > iou_thresh:
                suprimidos.add(j)
    return keep


class TrackManager:
    """
    Gestiona el ciclo de vida de tracks entre frames. Thread-safe.

    update() devuelve:
      - tracks "detectado"  → vistos en este frame, clase estable
      - tracks "detectando" → vistos en este frame, clase aún incierta
      - tracks "predictado" → NO vistos, pero se predice su posición por inercia
    """

    def __init__(self, timeout_frames: int = TIMEOUT_FRAMES,
                 max_pred_frames: int = MAX_PRED_FRAMES):
        self.timeout_frames  = timeout_frames
        self.max_pred_frames = max_pred_frames
        self._tracks: Dict[int, TrackInfo] = {}
        self._contados: Set[int] = set()
        self._frame_num: int = 0
        self._lock = threading.Lock()

    def reset(self):
        with self._lock:
            self._tracks.clear()
            self._contados.clear()
            self._frame_num = 0

    def update(self, detecciones: list) -> list:
        """
        Procesa las detecciones del frame actual y devuelve TODOS los tracks
        visibles (detectados + predichos), listos para dibujar en el overlay.
        """
        with self._lock:
            self._frame_num += 1
            activos: Set[int] = set()
            resultado = []

            # ── 0. NMS: eliminar cajas solapadas antes de actualizar tracks ──
            detecciones = _nms(detecciones, iou_thresh=0.55)

            # ── 1. Actualizar tracks detectados en este frame ─────────────────
            for det in detecciones:
                tid = det.get("track_id")
                if tid is None:
                    # Sin track_id → incluir como "detectando" sin predicción
                    resultado.append({
                        **det,
                        "clase_dominante":    det["nombre"],
                        "confianza_promedio": det["confianza"],
                        "estado":             "detectando",
                        "frames_sin_deteccion": 0,
                    })
                    continue

                activos.add(tid)

                if tid not in self._tracks:
                    self._tracks[tid] = TrackInfo(track_id=tid)

                t = self._tracks[tid]

                # Guardar posición anterior antes de actualizar
                if t.ultima_posicion:
                    t.prev_posicion = dict(t.ultima_posicion)

                t.historial_clases.append(det["nombre"])
                t.historial_confianza.append(det["confianza"])
                t.ultima_posicion = {k: det[k] for k in ("x1", "y1", "x2", "y2")}
                t.ultimo_frame_visto = self._frame_num
                t.frames_sin_deteccion = 0
                t.actualizar_velocidad()

                if not t.contado:
                    t.contado = True
                    self._contados.add(tid)

                estado = "detectado" if t.es_clase_estable else "detectando"
                resultado.append({
                    **det,
                    "clase_dominante":      t.clase_dominante,
                    "confianza_promedio":   t.confianza_promedio,
                    "contado":              t.contado,
                    "estado":               estado,
                    "frames_sin_deteccion": 0,
                })

            # ── 2. Predecir posición de tracks no vistos este frame ───────────
            cutoff = self._frame_num - self.timeout_frames
            to_delete = []

            for tid, t in self._tracks.items():
                if tid in activos:
                    continue

                t.frames_sin_deteccion += 1

                # Eliminar si lleva demasiado tiempo sin verse
                if t.ultimo_frame_visto < cutoff:
                    to_delete.append(tid)
                    continue

                # Predecir solo si la pérdida es corta (evita deriva excesiva)
                if t.frames_sin_deteccion > self.max_pred_frames:
                    continue

                pos = t.posicion_predicha(t.frames_sin_deteccion)
                if pos is None:
                    continue

                # Confianza decae con cada frame sin detección
                conf_pred = t.confianza_promedio * (0.88 ** t.frames_sin_deteccion)

                resultado.append({
                    "track_id":             tid,
                    "nombre":               t.clase_dominante,
                    "clase_dominante":      t.clase_dominante,
                    "confianza":            round(conf_pred, 4),
                    "confianza_promedio":   round(conf_pred, 4),
                    "contado":              t.contado,
                    "estado":               "predictado",
                    "frames_sin_deteccion": t.frames_sin_deteccion,
                    "color":                "#f59e0b",  # naranja para predichos
                    **pos,
                })

            for tid in to_delete:
                del self._tracks[tid]

            return resultado

    # ── Consultas ─────────────────────────────────────────────────────────────

    def get_conteo_unico(self) -> dict:
        with self._lock:
            conteo: Counter = Counter()
            for tid in self._contados:
                if tid in self._tracks:
                    conteo[self._tracks[tid].clase_dominante] += 1
            return dict(conteo)

    def get_total_unicos(self) -> int:
        with self._lock:
            return len(self._contados)


# ── Instancia global de cámara ────────────────────────────────────────────────
_cam_tracker = TrackManager()


def reset_cam_tracker():
    _cam_tracker.reset()


def get_cam_tracker() -> TrackManager:
    return _cam_tracker

"""
Sistema de tracking industrial — v3
====================================
Correcciones principales vs versión anterior:
  · Conteo por ESTABILIDAD (N frames), no al primer frame visto.
  · Buffer de Re-ID: track perdido → buffer → si reaparece hereda su estado.
    Evita contar el mismo objeto físico cuando ByteTrack le cambia el ID.
  · match_thresh y track_buffer corregidos en YAML (ver bytetrack_custom.yaml).
  · Métricas de depuración: FPS, IDs activos, IDs perdidos, re-IDs, contados.
  · Línea virtual de conteo (visual, opcional).
"""

import time
import threading
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

# ── Parámetros ────────────────────────────────────────────────────────────────
HISTORY_LEN         = 30   # frames de votación de clase por track
TIMEOUT_FRAMES      = 90   # frames sin detección antes de eliminar track
MAX_PRED_FRAMES     = 6    # máx frames de posición predicha (fantasma)
CLASES_ESTABLES     = 10   # frames mínimos ANTES de contar un objeto
CONF_MIN_TRACK      = 0.35 # confianza mínima para aceptar una detección
IMGSZ_DEFAULT       = 1280
CAM_WIDTH           = 1280
CAM_HEIGHT          = 720

# Re-ID: cuántos frames guardamos un track perdido para re-identificación
REID_BUFFER_FRAMES  = 60   # ≈3s a 20fps
REID_IOU_THRESH     = 0.20 # IoU mínimo para considerar re-ID válida
REID_SAME_CLASS     = True # exigir misma clase para re-ID

# Línea de conteo virtual — VERTICAL (fracción del ANCHO del frame)
COUNTING_LINE_FRAC  = 0.50 # 50 % del ancho (centro)

BYTETRACK_YAML = str(Path(__file__).resolve().parents[3] / "bytetrack_custom.yaml")


# ── Estructuras de datos ──────────────────────────────────────────────────────

@dataclass
class TrackInfo:
    track_id:   int
    frame_creado: int = 0

    historial_clases:    deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    historial_confianza: deque = field(default_factory=lambda: deque(maxlen=HISTORY_LEN))
    historial_x:         deque = field(default_factory=lambda: deque(maxlen=8))

    ultima_posicion: dict = field(default_factory=dict)
    prev_posicion:   dict = field(default_factory=dict)
    velocidad:       dict = field(default_factory=lambda: {"vx": 0.0, "vy": 0.0})

    ultimo_frame_visto:   int  = 0
    frames_sin_deteccion: int  = 0
    contado:              bool = False
    cruzado_linea:        bool = False

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

    def actualizar_velocidad(self):
        if not self.prev_posicion or not self.ultima_posicion:
            return
        cx = lambda p: (p["x1"] + p["x2"]) / 2
        cy = lambda p: (p["y1"] + p["y2"]) / 2
        dx = cx(self.ultima_posicion) - cx(self.prev_posicion)
        dy = cy(self.ultima_posicion) - cy(self.prev_posicion)
        a = 0.30
        self.velocidad["vx"] = a * dx + (1 - a) * self.velocidad["vx"]
        self.velocidad["vy"] = a * dy + (1 - a) * self.velocidad["vy"]

    def posicion_predicha(self, steps: int = 1) -> Optional[dict]:
        if not self.ultima_posicion:
            return None
        w = self.ultima_posicion["x2"] - self.ultima_posicion["x1"]
        h = self.ultima_posicion["y2"] - self.ultima_posicion["y1"]
        decay = 0.70 ** steps
        cx = (self.ultima_posicion["x1"] + self.ultima_posicion["x2"]) / 2
        cy = (self.ultima_posicion["y1"] + self.ultima_posicion["y2"]) / 2
        cx += self.velocidad["vx"] * decay
        cy += self.velocidad["vy"] * decay
        hw, hh = w / 2, h / 2
        cx = max(hw, min(CAM_WIDTH  - hw, cx))
        cy = max(hh, min(CAM_HEIGHT - hh, cy))
        return {"x1": int(cx-hw), "y1": int(cy-hh), "x2": int(cx+hw), "y2": int(cy+hh)}


@dataclass
class _ReidRecord:
    """Track perdido guardado para re-identificación."""
    track_id:     int
    clase:        str
    posicion:     dict
    frame_muerto: int
    contado:      bool
    cruzado:      bool


# ── NMS auxiliar ─────────────────────────────────────────────────────────────

def _iou(a: dict, b: dict) -> float:
    ix1 = max(a["x1"], b["x1"]); iy1 = max(a["y1"], b["y1"])
    ix2 = min(a["x2"], b["x2"]); iy2 = min(a["y2"], b["y2"])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = (a["x2"]-a["x1"]) * (a["y2"]-a["y1"])
    ub = (b["x2"]-b["x1"]) * (b["y2"]-b["y1"])
    return inter / (ua + ub - inter) if (ua + ub - inter) > 0 else 0.0


def _nms(dets: list, thresh: float = 0.45) -> list:
    if len(dets) <= 1:
        return dets
    ordered = sorted(dets, key=lambda d: d.get("confianza", 0), reverse=True)
    keep, sup = [], set()
    for i, d in enumerate(ordered):
        if i in sup:
            continue
        keep.append(d)
        for j in range(i + 1, len(ordered)):
            if j not in sup and _iou(d, ordered[j]) > thresh:
                sup.add(j)
    return keep


# ── TrackManager ──────────────────────────────────────────────────────────────

class TrackManager:
    """
    Gestiona tracks con:
    - Conteo por estabilidad (CLASES_ESTABLES frames antes de contar)
    - Buffer de Re-ID para evitar doble conteo tras cambio de ID
    - Predicción de posición (fantasma breve)
    - Métricas de depuración
    """

    def __init__(self,
                 timeout_frames: int   = TIMEOUT_FRAMES,
                 max_pred_frames: int  = MAX_PRED_FRAMES,
                 line_frac: float      = COUNTING_LINE_FRAC):
        self.timeout_frames  = timeout_frames
        self.max_pred_frames = max_pred_frames
        self.line_frac       = line_frac

        self._tracks: Dict[int, TrackInfo] = {}
        self._reid_buf: List[_ReidRecord]  = []
        self._contados: Set[int]           = set()   # track_ids contados
        self._frame_num: int               = 0
        self._lock                         = threading.Lock()

        # Métricas
        self._m_tracks_creados: int = 0
        self._m_total_contados: int = 0
        self._m_ids_perdidos:   int = 0
        self._m_reids:          int = 0
        self._fps_buf: deque        = deque(maxlen=20)
        self._ts_ultimo: float      = 0.0

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset(self):
        with self._lock:
            self._tracks.clear()
            self._reid_buf.clear()
            self._contados.clear()
            self._frame_num          = 0
            self._m_tracks_creados   = 0
            self._m_total_contados   = 0
            self._m_ids_perdidos     = 0
            self._m_reids            = 0
            self._fps_buf.clear()
            self._ts_ultimo          = 0.0

    # ── FPS ───────────────────────────────────────────────────────────────────

    def _tick_fps(self) -> float:
        now = time.time()
        if self._ts_ultimo > 0:
            self._fps_buf.append(now - self._ts_ultimo)
        self._ts_ultimo = now
        if len(self._fps_buf) < 2:
            return 0.0
        return round(1.0 / (sum(self._fps_buf) / len(self._fps_buf)), 1)

    # ── Re-ID ─────────────────────────────────────────────────────────────────

    def _buscar_reid(self, det: dict, clase: str) -> Optional[_ReidRecord]:
        """Busca en el buffer si esta detección corresponde a un track conocido."""
        cutoff = self._frame_num - REID_BUFFER_FRAMES
        best_iou, best = REID_IOU_THRESH, None
        for rec in self._reid_buf:
            if rec.frame_muerto < cutoff:
                continue
            if REID_SAME_CLASS and rec.clase != clase:
                continue
            v = _iou(det, rec.posicion)
            if v > best_iou:
                best_iou, best = v, rec
        return best

    # ── Cruce de línea ────────────────────────────────────────────────────────

    def _cruzo_linea(self, t: TrackInfo) -> bool:
        """True si el centro X acaba de cruzar la línea VERTICAL de conteo."""
        if t.cruzado_linea or len(t.historial_x) < 2:
            return False
        line = self.line_frac * CAM_WIDTH
        prev_x = t.historial_x[-2]
        curr_x = t.historial_x[-1]
        return (prev_x < line <= curr_x) or (prev_x > line >= curr_x)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, detecciones: list) -> list:
        with self._lock:
            fps = self._tick_fps()
            self._frame_num += 1
            activos: Set[int] = set()
            resultado = []

            # Filtro confianza + NMS
            detecciones = [d for d in detecciones if d.get("confianza", 0) >= CONF_MIN_TRACK]
            detecciones = _nms(detecciones, thresh=0.45)

            # ── 1. Procesar detecciones activas ───────────────────────────────
            for det in detecciones:
                tid = det.get("track_id")

                if tid is None:
                    resultado.append({
                        **det,
                        "clase_dominante":      det["nombre"],
                        "confianza_promedio":   det["confianza"],
                        "estado":               "detectando",
                        "frames_sin_deteccion": 0,
                        "contado":              False,
                    })
                    continue

                activos.add(tid)
                clase_det = det["nombre"]

                # Crear track nuevo o recuperarlo
                if tid not in self._tracks:
                    t = TrackInfo(track_id=tid, frame_creado=self._frame_num)
                    self._tracks[tid] = t
                    self._m_tracks_creados += 1

                    # Intentar re-ID con track perdido
                    reid = self._buscar_reid(det, clase_det)
                    if reid:
                        t.contado       = reid.contado
                        t.cruzado_linea = reid.cruzado
                        if reid.contado:
                            self._contados.add(tid)
                        self._reid_buf = [r for r in self._reid_buf if r.track_id != reid.track_id]
                        self._m_reids += 1
                else:
                    t = self._tracks[tid]

                # Actualizar historial
                if t.ultima_posicion:
                    t.prev_posicion = dict(t.ultima_posicion)
                t.historial_clases.append(clase_det)
                t.historial_confianza.append(det["confianza"])
                t.ultima_posicion      = {k: det[k] for k in ("x1","y1","x2","y2")}
                t.ultimo_frame_visto   = self._frame_num
                t.frames_sin_deteccion = 0
                t.actualizar_velocidad()

                cx = (det["x1"] + det["x2"]) / 2.0
                t.historial_x.append(cx)

                # ── Lógica de conteo ─────────────────────────────────────────
                if not t.contado and t.es_clase_estable:
                    # Opción A: cruzó la línea virtual
                    if self._cruzo_linea(t):
                        t.contado = True
                        t.cruzado_linea = True
                        self._contados.add(tid)
                        self._m_total_contados += 1
                    # Opción B: lleva suficientes frames estable (objeto estático)
                    elif (self._frame_num - t.frame_creado) >= CLASES_ESTABLES * 2:
                        t.contado = True
                        self._contados.add(tid)
                        self._m_total_contados += 1

                estado = "detectado" if t.es_clase_estable else "detectando"
                resultado.append({
                    **det,
                    "clase_dominante":      t.clase_dominante,
                    "confianza_promedio":   t.confianza_promedio,
                    "contado":              t.contado,
                    "estado":               estado,
                    "frames_sin_deteccion": 0,
                })

            # ── 2. Tracks no vistos este frame ────────────────────────────────
            cutoff     = self._frame_num - self.timeout_frames
            to_delete  = []

            for tid, t in self._tracks.items():
                if tid in activos:
                    continue
                t.frames_sin_deteccion += 1

                if t.ultimo_frame_visto < cutoff:
                    to_delete.append(tid)
                    continue

                if t.frames_sin_deteccion > self.max_pred_frames:
                    continue

                pos = t.posicion_predicha(t.frames_sin_deteccion)
                if pos is None:
                    continue

                conf_pred = t.confianza_promedio * (0.75 ** t.frames_sin_deteccion)
                resultado.append({
                    "track_id":             tid,
                    "nombre":               t.clase_dominante,
                    "clase_dominante":      t.clase_dominante,
                    "confianza":            round(conf_pred, 4),
                    "confianza_promedio":   round(conf_pred, 4),
                    "contado":              t.contado,
                    "estado":               "predictado",
                    "frames_sin_deteccion": t.frames_sin_deteccion,
                    "color":                "#f59e0b",
                    **pos,
                })

            # Mover expirados al buffer de re-ID
            for tid in to_delete:
                t = self._tracks.pop(tid)
                if t.ultima_posicion and t.clase_dominante != "Detectando...":
                    self._reid_buf.append(_ReidRecord(
                        track_id    = tid,
                        clase       = t.clase_dominante,
                        posicion    = dict(t.ultima_posicion),
                        frame_muerto= self._frame_num,
                        contado     = t.contado,
                        cruzado     = t.cruzado_linea,
                    ))
                self._m_ids_perdidos += 1

            # Limpiar buffer caducado
            cutoff_reid = self._frame_num - REID_BUFFER_FRAMES
            self._reid_buf = [r for r in self._reid_buf if r.frame_muerto >= cutoff_reid]

            return resultado

    # ── Consultas ─────────────────────────────────────────────────────────────

    def get_conteo_unico(self) -> dict:
        with self._lock:
            conteo: Counter = Counter()
            for tid in self._contados:
                if tid in self._tracks:
                    clase = self._tracks[tid].clase_dominante
                    if clase != "Detectando...":
                        conteo[clase] += 1
            return dict(conteo)

    def get_total_unicos(self) -> int:
        with self._lock:
            return self._m_total_contados

    def get_metricas(self) -> dict:
        with self._lock:
            fps = 0.0
            if len(self._fps_buf) >= 2:
                fps = round(1.0 / (sum(self._fps_buf) / len(self._fps_buf)), 1)
            return {
                "fps":             fps,
                "ids_activos":     len(self._tracks),
                "ids_perdidos":    self._m_ids_perdidos,
                "tracks_creados":  self._m_tracks_creados,
                "total_contados":  self._m_total_contados,
                "reids_usados":    self._m_reids,
                "reid_buf_size":   len(self._reid_buf),
                "linea_x_frac":    self.line_frac,
            }


# ── Instancia global ──────────────────────────────────────────────────────────
_cam_tracker = TrackManager()


def reset_cam_tracker():
    _cam_tracker.reset()


def get_cam_tracker() -> TrackManager:
    return _cam_tracker

"""
Procesamiento de video con ByteTrack en un hilo daemon.
Usa model.track(stream=True, persist=True) para iterar frames sin cargar
todo el video en memoria, y TrackManager para conteo único y clase dominante.
"""
import os
import threading

import cv2

from .tracker_service import TrackManager, CONF_DEFAULT, IMGSZ_DEFAULT

_lock = threading.Lock()
_estado = {
    "running":              False,
    "frames_total":         0,
    "frames_procesados":    0,
    "frames_con_deteccion": 0,
    "errores":              0,
    "error_fatal":          None,
    "resultado": {
        "materiales_encontrados": {},
        "objeto_mas_frecuente":   None,
        "total_objetos":          0,
        "total_unicos":           0,
    },
}


class VideoProcessor:
    """
    Procesa un archivo de video con ByteTrack en un hilo daemon.

    Parámetros configurables:
        conf         — umbral de confianza (default 0.25)
        imgsz        — tamaño de imagen para YOLO (default 640)
        saltar_frames — procesar 1 de cada N frames (default 1 = todos)
    """

    def __init__(self, conf: float = CONF_DEFAULT,
                 imgsz: int = IMGSZ_DEFAULT,
                 saltar_frames: int = 1):
        self.conf         = conf
        self.imgsz        = imgsz
        self.saltar_frames = max(1, saltar_frames)

    def procesar_video(self, ruta_video: str) -> threading.Thread:
        hilo = threading.Thread(
            target=self._worker,
            args=(ruta_video,),
            daemon=True,
        )
        hilo.start()
        return hilo

    def _worker(self, ruta_video: str):
        global _estado

        # Contar frames totales para barra de progreso
        cap = cv2.VideoCapture(ruta_video)
        if not cap.isOpened():
            with _lock:
                _estado["error_fatal"] = f"No se pudo abrir: {ruta_video}"
                _estado["running"] = False
            return

        total_frames_raw = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        cap.release()

        frames_a_procesar = max(1, total_frames_raw // self.saltar_frames)

        with _lock:
            _estado.update({
                "running":              True,
                "frames_total":         frames_a_procesar,
                "frames_procesados":    0,
                "frames_con_deteccion": 0,
                "errores":              0,
                "error_fatal":          None,
                "resultado": {
                    "materiales_encontrados": {},
                    "objeto_mas_frecuente":   None,
                    "total_objetos":          0,
                    "total_unicos":           0,
                },
            })

        tracker = TrackManager()
        frames_procesados = 0

        try:
            # Import tardío para evitar ciclos Django al arrancar
            from .yolo_service import _cargar_modelo

            model = _cargar_modelo()

            # stream=True → generador frame a frame sin cargar todo en RAM
            # persist=True → ByteTrack mantiene IDs entre frames
            from .tracker_service import BYTETRACK_YAML
            gen = model.track(
                source=ruta_video,
                persist=True,
                tracker=BYTETRACK_YAML,
                conf=self.conf,
                imgsz=self.imgsz,
                verbose=False,
                stream=True,
            )

            frame_idx = 0
            for result in gen:
                if frame_idx % self.saltar_frames != 0:
                    frame_idx += 1
                    continue

                try:
                    detecciones_raw = _extraer_detecciones(result)
                    detecciones     = tracker.update(detecciones_raw)

                    if detecciones:
                        with _lock:
                            _estado["frames_con_deteccion"] += 1

                except Exception:
                    with _lock:
                        _estado["errores"] += 1

                frames_procesados += 1
                with _lock:
                    _estado["frames_procesados"] = frames_procesados

                frame_idx += 1

        except FileNotFoundError:
            with _lock:
                _estado["error_fatal"] = (
                    "Modelo YOLO no encontrado. "
                    "Verifica que apps/clasificacion/models/best.pt exista."
                )
        except Exception as exc:
            with _lock:
                _estado["error_fatal"] = str(exc)
        finally:
            conteo   = tracker.get_conteo_unico()
            unicos   = tracker.get_total_unicos()
            frecuente = (
                max(conteo, key=conteo.get) if conteo else None
            )
            with _lock:
                _estado["running"] = False
                _estado["resultado"] = {
                    "materiales_encontrados": conteo,
                    "objeto_mas_frecuente":   frecuente,
                    "total_objetos":          sum(conteo.values()),
                    "total_unicos":           unicos,
                }

            # Limpiar archivo temporal si fue subido
            if ruta_video.startswith(os.path.join(os.sep, "tmp")) or \
               ruta_video.startswith(os.path.join(os.sep, "temp")):
                try:
                    os.remove(ruta_video)
                except OSError:
                    pass


def _extraer_detecciones(result) -> list:
    """Convierte un resultado de model.track() en lista de dicts estándar."""
    from .yolo_service import _normalizar, _traducir, IGNORAR

    detecciones = []
    if result.boxes is None:
        return detecciones

    nombres = result.names
    ids     = result.boxes.id

    for i, box in enumerate(result.boxes):
        clase_id   = int(box.cls[0])
        nombre_orig = str(nombres[clase_id]).strip()

        if _normalizar(nombre_orig) in IGNORAR:
            continue

        conf       = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        nombre_es  = _traducir(nombre_orig)
        track_id   = int(ids[i].item()) if ids is not None else None

        detecciones.append({
            "track_id": track_id,
            "nombre":   nombre_es,
            "confianza": round(conf, 4),
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "color": "#00c853",
        })

    return detecciones


# ── Singleton y funciones públicas ────────────────────────────────────────────

_processor = VideoProcessor(conf=CONF_DEFAULT, imgsz=IMGSZ_DEFAULT, saltar_frames=1)


def iniciar_procesamiento_video(ruta_video: str) -> threading.Thread:
    return _processor.procesar_video(ruta_video)


def get_estado_video() -> dict:
    with _lock:
        return dict(_estado)

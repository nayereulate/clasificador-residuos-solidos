from collections import Counter
from pathlib import Path
from datetime import datetime
import re

import cv2
import numpy as np
import torch
from django.conf import settings
from ultralytics import YOLO

# GPU si está disponible — se aplica en todas las llamadas de tracking
_DEVICE = 0 if torch.cuda.is_available() else "cpu"

# =========================================================
# MODELO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
MODELO_RESIDUOS = BASE_DIR / "models" / "best.pt"
_MODEL = None

# =========================================================
# FILTRO DE OBJETOS QUE NO QUEREMOS MOSTRAR
# =========================================================
# Nombres en inglés tal como los devuelve YOLO (se comparan en minúsculas)

IGNORAR = {
    "plastic bottle cap",
    "pop tab",
    "metal lid",
    "plastic lid",
    "metal bottle cap",
    "six pack rings",
    "rope - strings",
    "shoe",               # no es residuo reciclable
    "spread tub",         # redundante con "other plastic container"
    "squeezable tube",    # cubierto por "Tubo flexible"
}

# =========================================================
# TRADUCCIÓN
# =========================================================

TRADUCCION = {
    "aerosol": "Aerosol",
    "aluminium blister pack": "Blíster de aluminio",
    "aluminium foil": "Papel aluminio",
    "battery": "Batería",
    "broken glass": "Vidrio roto",
    "clear plastic bottle": "Botella plástica transparente",
    "corrugated carton": "Cartón corrugado",
    "crisp packet": "Bolsa de snacks",
    "disposable food container": "Envase desechable de comida",
    "disposable plastic cup": "Vaso plástico desechable",
    "drink can": "Lata",
    "drink carton": "Envase de bebida",
    "egg carton": "Cartón de huevos",
    "foam cup": "Vaso de espuma",
    "foam food container": "Envase de espuma",
    "food can": "Lata de alimentos",
    "food waste": "Desecho orgánico",
    "garbage bag": "Bolsa de basura",
    "glass bottle": "Botella de vidrio",
    "glass cup": "Vaso de vidrio",
    "glass jar": "Frasco de vidrio",
    "magazine paper": "Papel de revista",
    "meal carton": "Envase de comida",
    "metal bottle cap": "Tapa metálica de botella",
    "metal lid": "Tapa metálica",
    "normal paper": "Papel",
    "other carton": "Otro cartón",
    "other plastic": "Otro plástico",
    "other plastic bottle": "Otra botella plástica",
    "other plastic container": "Otro envase plástico",
    "other plastic cup": "Otro vaso plástico",
    "other plastic wrapper": "Otro envoltorio plástico",
    "paper bag": "Bolsa de papel",
    "paper cup": "Vaso de papel",
    "paper straw": "Pajilla de papel",
    "pizza box": "Caja de pizza",
    "plastic bottle cap": "Tapa plástica de botella",
    "plastic film": "Film plástico",
    "plastic glooves": "Guantes plásticos",
    "plastic lid": "Tapa plástica",
    "plastic straw": "Pajilla plástica",
    "plastic utensils": "Cubiertos plásticos",
    "polypropylene bag": "Bolsa de polipropileno",
    "pop tab": "Anilla de lata",
    "rope - strings": "Cuerdas",
    "scrap metal": "Chatarra metálica",
    "shoe": "Zapato",
    "single-use carrier bag": "Bolsa de un solo uso",
    "six pack rings": "Aros de seis latas",
    "spread tub": "Envase para untable",
    "squeezable tube": "Tubo flexible",
    "styrofoam piece": "Trozo de unicel",
    "tissues": "Pañuelos",
    "toilet tube": "Tubo de cartón higiénico",
    "tupperware": "Tupperware",
    "wrapping paper": "Papel de envoltura",
    "can": "Lata",
    "cardboard": "Cartón",
    "paper": "Papel",
    "plastic bag": "Bolsa plástica",
    "plastic bottle": "Botella plástica",
}

# =========================================================
# HELPERS
# =========================================================

def _normalizar(texto):
    return str(texto).strip().lower()


def _sanitizar_nombre(texto):
    texto = _normalizar(texto)
    texto = re.sub(r"[^a-z0-9_-]+", "_", texto)
    texto = texto.strip("_")
    return texto or "analisis"


def _traducir(nombre):
    clave = _normalizar(nombre)
    return TRADUCCION.get(clave, str(nombre).replace("_", " ").title())


def _cargar_modelo():
    global _MODEL

    if _MODEL is not None:
        return _MODEL

    if not MODELO_RESIDUOS.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo entrenado en: {MODELO_RESIDUOS}"
        )

    _MODEL = YOLO(str(MODELO_RESIDUOS))
    return _MODEL


def _guardar_imagen_anotada(imagen, nombre_base=None):
    """
    Guarda la imagen anotada dentro de MEDIA_ROOT/analizados/
    y devuelve la URL relativa.
    """
    media_root = Path(getattr(settings, "MEDIA_ROOT", BASE_DIR / "media"))
    media_url = getattr(settings, "MEDIA_URL", "/media/")

    salida_dir = media_root / "analizados"
    salida_dir.mkdir(parents=True, exist_ok=True)

    if not nombre_base:
        nombre_base = f"analisis_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    nombre_base = _sanitizar_nombre(nombre_base)
    nombre_archivo = f"{nombre_base}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_procesada.jpg"
    salida_path = salida_dir / nombre_archivo

    ok = cv2.imwrite(str(salida_path), imagen)
    if not ok:
        raise IOError(f"No se pudo guardar la imagen procesada en {salida_path}")

    return f"{media_url.rstrip('/')}/analizados/{nombre_archivo}"


# =========================================================
# DETECCIÓN
# =========================================================

def detectar_objetos(ruta_imagen, nombre_base=None, imgsz=640, guardar_imagen=True):
    """
    Detecta residuos usando best.pt.

    Devuelve:
    - objeto_principal
    - confianza
    - objetos
    - detecciones
    - boxes
    - total / cantidad_total
    - imagen_procesada
    """
    model = _cargar_modelo()
    results = model.predict(
        ruta_imagen,
        imgsz=imgsz,
        iou=0.45,      # NMS agresivo: suprime duplicados del mismo objeto
        conf=0.25,     # umbral mínimo de confianza para imagen estática
        verbose=False,
    )

    imagen = cv2.imread(ruta_imagen)
    if imagen is None:
        raise FileNotFoundError(f"No se pudo abrir la imagen: {ruta_imagen}")

    imagen_anotada = imagen.copy() if guardar_imagen else None

    objetos = Counter()
    detecciones = []
    boxes_result = []

    confianza_maxima = 0.0
    objeto_principal = "Sin detección"

    for r in results:
        nombres_clase = r.names

        for box in r.boxes:
            clase_id = int(box.cls[0])
            nombre_original = str(nombres_clase[clase_id]).strip()
            nombre_normalizado = _normalizar(nombre_original)

            if nombre_normalizado in IGNORAR:
                continue

            confianza = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            nombre_es = _traducir(nombre_original)

            objetos[nombre_es] += 1

            detecciones.append({
                "nombre": nombre_es,
                "confianza": round(confianza, 4),
            })

            boxes_result.append({
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "label": nombre_es,
                "confianza": round(confianza, 4),
                "color": "#00c853",
            })

            if confianza > confianza_maxima:
                confianza_maxima = confianza
                objeto_principal = nombre_es

            if guardar_imagen and imagen_anotada is not None:
                color_bgr = (83, 200, 83)

                cv2.rectangle(
                    imagen_anotada,
                    (x1, y1),
                    (x2, y2),
                    color_bgr,
                    3
                )

                etiqueta = f"{nombre_es} {confianza:.2f}"
                (tw, th), baseline = cv2.getTextSize(
                    etiqueta,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    2
                )

                y_texto = y1 - th - baseline - 10
                if y_texto < 0:
                    y_texto = y2 + th + baseline + 12

                cv2.rectangle(
                    imagen_anotada,
                    (x1, max(0, y_texto - th - baseline - 6)),
                    (x1 + tw + 12, max(0, y_texto + baseline + 6)),
                    color_bgr,
                    -1
                )

                cv2.putText(
                    imagen_anotada,
                    etiqueta,
                    (x1 + 6, y_texto),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

    if guardar_imagen and imagen_anotada is not None and not objetos:
        cv2.putText(
            imagen_anotada,
            "Sin detecciones",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

    imagen_procesada = ""
    if guardar_imagen and imagen_anotada is not None:
        imagen_procesada = _guardar_imagen_anotada(
            imagen_anotada,
            nombre_base=nombre_base or Path(ruta_imagen).stem
        )

    objetos_ordenados = dict(
        sorted(
            objetos.items(),
            key=lambda item: (-item[1], item[0])
        )
    )

    detecciones_ordenadas = sorted(
        detecciones,
        key=lambda item: (-item["confianza"], item["nombre"])
    )

    total = sum(objetos.values())

    return {
        "objeto_principal": objeto_principal,
        "confianza": round(confianza_maxima, 4),
        "objetos": objetos_ordenados,
        "detecciones": detecciones_ordenadas,
        "boxes": boxes_result,
        "total": total,
        "cantidad_total": total,
        "imagen_procesada": imagen_procesada,
    }


# =========================================================
# COLORES POR MATERIAL (BGR para OpenCV / HEX para canvas JS)
# =========================================================

MATERIAL_DESDE_CLASE: dict = {}   # poblado lazy por _build_material_map()

# Mapa material → color HEX para overlay JS
COLOR_POR_MATERIAL = {
    "Metal":        "#94a3b8",   # gris plateado
    "Vidrio":       "#67e8f9",   # cian
    "Plástico":     "#60a5fa",   # azul
    "Papel/Cartón": "#fbbf24",   # ámbar
    "Orgánico":     "#4ade80",   # verde
    "Espuma/EPS":   "#e2e8f0",   # blanco grisáceo
    "Otro":         "#f87171",   # rojo suave
}
COLOR_DEFAULT = "#52b788"


def _build_material_map() -> dict:
    """Construye un dict {nombre_es: material} desde MATERIAL_RULES para colorear."""
    from apps.clasificacion.administracion_service import MATERIAL_RULES
    mapping = {}
    for rule in MATERIAL_RULES:
        obj = rule["if"].get("objeto", "")
        mat = rule["then"].get("material", "Otro")
        if obj:
            mapping[obj] = mat
    return mapping


def _color_para(nombre_es: str) -> str:
    global MATERIAL_DESDE_CLASE
    if not MATERIAL_DESDE_CLASE:
        try:
            MATERIAL_DESDE_CLASE = _build_material_map()
        except Exception:
            pass
    mat = MATERIAL_DESDE_CLASE.get(nombre_es, "Otro")
    return COLOR_POR_MATERIAL.get(mat, COLOR_DEFAULT)


# =========================================================
# TRACKING (ByteTrack)
# =========================================================

# Umbrales calibrados para reducir falsos positivos y duplicados
TRACKING_CONF  = 0.35   # más alto → menos ruido y falsos positivos
TRACKING_IMGSZ = 1280   # alta resolución → detecta objetos pequeños/lejanos
TRACKING_IOU   = 0.50   # NMS más agresivo: elimina cajas solapadas del mismo objeto


def detectar_con_track(frame: np.ndarray,
                        conf: float = TRACKING_CONF,
                        imgsz: int  = TRACKING_IMGSZ,
                        iou: float  = TRACKING_IOU) -> list:
    """
    Detecta y rastrea objetos en un frame numpy (BGR) usando ByteTrack.

    - persist=True  → el tracker recuerda IDs entre frames
    - half=True     → FP16 en GPU (más rápido, igual precisión)
    - iou=0.45      → NMS agresivo: elimina cajas duplicadas del mismo objeto
    """
    from .tracker_service import BYTETRACK_YAML
    model = _cargar_modelo()

    results = model.track(
        source=frame,
        persist=True,
        tracker=BYTETRACK_YAML,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        device=_DEVICE,
        half=torch.cuda.is_available(),   # FP16 solo si hay GPU
        verbose=False,
    )

    # Área mínima de caja para ignorar detecciones ruido (px²)
    MIN_BOX_AREA = 400   # 20×20 px mínimo

    detecciones = []
    for r in results:
        if r.boxes is None:
            continue

        nombres_clase = r.names
        ids = r.boxes.id  # tensor o None cuando no hay tracks asignados

        for i, box in enumerate(r.boxes):
            clase_id           = int(box.cls[0])
            nombre_original    = str(nombres_clase[clase_id]).strip()
            nombre_normalizado = _normalizar(nombre_original)

            if nombre_normalizado in IGNORAR:
                continue

            confianza = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            # Descartar cajas demasiado pequeñas (ruido del modelo)
            area = (x2 - x1) * (y2 - y1)
            if area < MIN_BOX_AREA:
                continue

            nombre_es = _traducir(nombre_original)
            track_id  = int(ids[i].item()) if ids is not None else None
            color     = _color_para(nombre_es)

            detecciones.append({
                "track_id": track_id,
                "nombre":   nombre_es,
                "confianza": round(confianza, 4),
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "color": color,
            })

    return detecciones


def reset_tracker():
    """
    Reinicia el estado interno del tracker ByteTrack.
    Llamar al iniciar una nueva sesión de cámara.
    """
    global _MODEL
    if _MODEL is not None:
        try:
            # Ultralytics almacena el tracker en predictor; borrarlo fuerza reinicio
            if hasattr(_MODEL, "predictor") and _MODEL.predictor is not None:
                _MODEL.predictor = None
        except Exception:
            pass
"""
Módulo 2 – Servicio de Administración de Residuos
==================================================
Arquitectura:
  resultado_json (Módulo 1)
      ↓
  Grammar Engine (validación + reglas)
      ↓
  MaterialClassifierFactory  (Patrón Factory)
      ↓
  PriorityQueue             (cola.PriorityQueue)
      ↓
  Alertas
      ↓
  ExportStrategy            (Patrón Strategy → JSON / XML / TXT)
"""

import json
import logging
import queue
import threading
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections import defaultdict

logger = logging.getLogger(__name__)

from grammar_engine.engine import GrammarEngine

# ──────────────────────────────────────────────────────────────────────────────
# GRAMÁTICA Y REGLAS PARA EL MÓDULO 2
# ──────────────────────────────────────────────────────────────────────────────

GRAMMAR_MODULO2 = {
    "objeto": {
        "required": True,
        "type": str,
    },
    "cantidad": {
        "required": True,
        "type": int,
        "min": 0,
    },
}

MATERIAL_RULES = [
    # ── Metal ──────────────────────────────────────────────────────────────────
    # peso_medio_kg: peso genérico estimado por unidad (kg)
    {"if": {"objeto": "Lata"},                          "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.015}},
    {"if": {"objeto": "Lata de alimentos"},             "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.050}},
    {"if": {"objeto": "Aerosol"},                       "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.150}},
    {"if": {"objeto": "Batería"},                       "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.500}},
    {"if": {"objeto": "Papel aluminio"},                "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Blíster de aluminio"},           "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.005}},
    {"if": {"objeto": "drink can"},                     "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.015}},
    {"if": {"objeto": "food can"},                      "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.050}},
    {"if": {"objeto": "aerosol"},                       "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.150}},
    # ── Vidrio ─────────────────────────────────────────────────────────────────
    {"if": {"objeto": "Botella de vidrio"},             "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.300}},
    {"if": {"objeto": "Vaso de vidrio"},                "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.200}},
    {"if": {"objeto": "Frasco de vidrio"},              "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.150}},
    {"if": {"objeto": "Vidrio roto"},                   "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.100}},
    {"if": {"objeto": "glass bottle"},                  "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.300}},
    {"if": {"objeto": "wine glass"},                    "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.180}},
    {"if": {"objeto": "glass cup"},                     "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.200}},
    {"if": {"objeto": "glass jar"},                     "then": {"material": "Vidrio",       "prioridad_base": 2, "peso_medio_kg": 0.150}},
    # ── Plástico ───────────────────────────────────────────────────────────────
    {"if": {"objeto": "Botella plástica transparente"}, "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.025}},
    {"if": {"objeto": "Otra botella plástica"},         "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.030}},
    {"if": {"objeto": "Otro plástico"},                 "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Otro envase plástico"},          "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Otro vaso plástico"},            "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.005}},
    {"if": {"objeto": "Vaso plástico desechable"},      "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.005}},
    {"if": {"objeto": "Film plástico"},                 "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.010}},
    {"if": {"objeto": "Bolsa de polipropileno"},        "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.008}},
    {"if": {"objeto": "Bolsa de snacks"},               "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.010}},
    {"if": {"objeto": "Guantes plásticos"},             "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.015}},
    {"if": {"objeto": "Pajilla plástica"},              "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.001}},
    {"if": {"objeto": "Cubiertos plásticos"},           "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.015}},
    {"if": {"objeto": "Envase desechable de comida"},   "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Otro envoltorio plástico"},      "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.012}},
    {"if": {"objeto": "bottle"},                        "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.025}},
    {"if": {"objeto": "cup"},                           "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.005}},
    {"if": {"objeto": "clear plastic bottle"},          "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.025}},
    {"if": {"objeto": "other plastic bottle"},          "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.030}},
    {"if": {"objeto": "plastic straw"},                 "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.001}},
    # ── Papel / Cartón ─────────────────────────────────────────────────────────
    {"if": {"objeto": "Cartón corrugado"},              "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.200}},
    {"if": {"objeto": "Cartón de huevos"},              "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.060}},
    {"if": {"objeto": "Otro cartón"},                   "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.100}},
    {"if": {"objeto": "Caja de pizza"},                 "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.120}},
    {"if": {"objeto": "Papel"},                         "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.005}},
    {"if": {"objeto": "Papel de revista"},              "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.100}},
    {"if": {"objeto": "Bolsa de papel"},                "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Vaso de papel"},                 "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.010}},
    {"if": {"objeto": "Pajilla de papel"},              "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.001}},
    {"if": {"objeto": "Envase de bebida"},              "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.040}},
    {"if": {"objeto": "Envase de comida"},              "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.030}},
    {"if": {"objeto": "corrugated carton"},             "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.200}},
    {"if": {"objeto": "pizza box"},                     "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.120}},
    {"if": {"objeto": "normal paper"},                  "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.005}},
    {"if": {"objeto": "paper bag"},                     "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "paper cup"},                     "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.010}},
    # ── Orgánico ───────────────────────────────────────────────────────────────
    {"if": {"objeto": "Desecho orgánico"},              "then": {"material": "Orgánico",     "prioridad_base": 5, "peso_medio_kg": 0.200}},
    {"if": {"objeto": "food waste"},                    "then": {"material": "Orgánico",     "prioridad_base": 5, "peso_medio_kg": 0.200}},
    # ── Espuma ─────────────────────────────────────────────────────────────────
    {"if": {"objeto": "Vaso de espuma"},                "then": {"material": "Espuma/EPS",   "prioridad_base": 3, "peso_medio_kg": 0.003}},
    {"if": {"objeto": "Envase de espuma"},              "then": {"material": "Espuma/EPS",   "prioridad_base": 3, "peso_medio_kg": 0.012}},
    {"if": {"objeto": "foam cup"},                      "then": {"material": "Espuma/EPS",   "prioridad_base": 3, "peso_medio_kg": 0.003}},
    {"if": {"objeto": "foam food container"},           "then": {"material": "Espuma/EPS",   "prioridad_base": 3, "peso_medio_kg": 0.012}},
    # ── Bolsa de basura / Otro ─────────────────────────────────────────────────
    {"if": {"objeto": "Bolsa de basura"},               "then": {"material": "Otro",         "prioridad_base": 6, "peso_medio_kg": 0.025}},
    {"if": {"objeto": "garbage bag"},                   "then": {"material": "Otro",         "prioridad_base": 6, "peso_medio_kg": 0.025}},
    {"if": {"objeto": "Zapato"},                        "then": {"material": "Otro",         "prioridad_base": 6, "peso_medio_kg": 0.400}},
    {"if": {"objeto": "Cuerdas"},                       "then": {"material": "Otro",         "prioridad_base": 6, "peso_medio_kg": 0.050}},
    {"if": {"objeto": "Trozo de unicel"},               "then": {"material": "Espuma/EPS",   "prioridad_base": 3, "peso_medio_kg": 0.008}},
    # ── Clases adicionales del vocabulario de YOLO (sin regla previa) ──────────
    {"if": {"objeto": "Chatarra metálica"},             "then": {"material": "Metal",        "prioridad_base": 1, "peso_medio_kg": 0.800}},
    {"if": {"objeto": "Bolsa plástica"},                "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.008}},
    {"if": {"objeto": "Botella plástica"},              "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.025}},
    {"if": {"objeto": "Cartón"},                        "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.100}},
    {"if": {"objeto": "Bolsa de un solo uso"},          "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.008}},
    {"if": {"objeto": "Envase para untable"},           "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.035}},
    {"if": {"objeto": "Tubo flexible"},                 "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Pañuelos"},                      "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.010}},
    {"if": {"objeto": "Tubo de cartón higiénico"},      "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.015}},
    {"if": {"objeto": "Papel de envoltura"},            "then": {"material": "Papel/Cartón", "prioridad_base": 4, "peso_medio_kg": 0.020}},
    {"if": {"objeto": "Tupperware"},                    "then": {"material": "Plástico",     "prioridad_base": 3, "peso_medio_kg": 0.080}},
]

# Prioridad de recolección por material (Metal/Vidrio = Alta; Plástico/EPS = Media; Papel/Orgánico = Baja)
MATERIAL_PRIORITY_LABEL = {
    "Metal":        "Alta",
    "Vidrio":       "Alta",
    "Plástico":     "Media",
    "Espuma/EPS":   "Media",
    "Papel/Cartón": "Baja",
    "Orgánico":     "Baja",
    "Otro":         "Baja",
}

# Mapas de colores Bootstrap para la plantilla
MATERIAL_COLORS = {
    "Metal":        "secondary",
    "Vidrio":       "info",
    "Plástico":     "primary",
    "Papel/Cartón": "warning",
    "Orgánico":     "success",
    "Espuma/EPS":   "light",
    "Otro":         "dark",
}

PRIORITY_COLORS = {
    "Alta":  "danger",
    "Media": "warning",
    "Baja":  "success",
}

MATERIAL_PRIORITY_LEVEL = {
    "Metal":        1,
    "Vidrio":       2,
    "Plástico":     3,
    "Espuma/EPS":   3,
    "Papel/Cartón": 4,
    "Orgánico":     5,
    "Otro":         6,
}


# ══════════════════════════════════════════════════════════════════════════════
# PATRÓN FACTORY – MaterialClassifier
# ══════════════════════════════════════════════════════════════════════════════

class MaterialClassifier(ABC):
    """Interfaz abstracta para clasificadores de material."""

    @abstractmethod
    def classify(self, objeto: str, cantidad: int) -> dict:
        pass


class GrammarMaterialClassifier(MaterialClassifier):
    """
    Clasificador que delega en Grammar Engine.
    Valida la entrada con GRAMMAR_MODULO2 y aplica MATERIAL_RULES
    para determinar el material y la prioridad base de cada objeto.
    """

    def __init__(self):
        self._engine = GrammarEngine()

    def classify(self, objeto: str, cantidad: int) -> dict:
        data = {"objeto": objeto, "cantidad": cantidad}
        try:
            result = self._engine.process(data, GRAMMAR_MODULO2, MATERIAL_RULES)
        except Exception:
            result = dict(data)

        if "material" not in result:
            result["material"] = "Otro"
            result["prioridad_base"] = 6

        return result


class DefaultMaterialClassifier(MaterialClassifier):
    """Clasificador de respaldo cuando Grammar Engine no está disponible."""

    def classify(self, objeto: str, cantidad: int) -> dict:
        return {
            "objeto":       objeto,
            "cantidad":     cantidad,
            "material":     "Otro",
            "prioridad_base": 6,
        }


class MaterialClassifierFactory:
    """
    Patrón Factory.
    Decide qué implementación de MaterialClassifier instanciar
    según el tipo solicitado.
    """

    _registry = {
        "grammar": GrammarMaterialClassifier,
        "default": DefaultMaterialClassifier,
    }

    @staticmethod
    def create(classifier_type: str = "grammar") -> MaterialClassifier:
        cls = MaterialClassifierFactory._registry.get(classifier_type)
        if cls is None:
            raise ValueError(f"Clasificador desconocido: {classifier_type!r}")
        return cls()


# ══════════════════════════════════════════════════════════════════════════════
# PATRÓN STRATEGY – Export
# ══════════════════════════════════════════════════════════════════════════════

class ExportStrategy(ABC):
    """Interfaz abstracta para estrategias de exportación."""

    @abstractmethod
    def export(self, data: dict) -> str:
        pass


class JsonExportStrategy(ExportStrategy):
    def export(self, data: dict) -> str:
        return json.dumps(data, indent=4, ensure_ascii=False)


class XmlExportStrategy(ExportStrategy):
    def export(self, data: dict) -> str:
        root = ET.Element("administracion_residuos")

        def _add(parent, key, value):
            tag = key.replace(" ", "_").replace("/", "_")
            child = ET.SubElement(parent, tag)
            if isinstance(value, dict):
                for k, v in value.items():
                    _add(child, str(k), v)
            elif isinstance(value, list):
                for item in value:
                    item_el = ET.SubElement(child, "item")
                    item_el.text = str(item)
            else:
                child.text = str(value)

        for key, value in data.items():
            _add(root, key, value)

        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode", xml_declaration=True)


class TxtExportStrategy(ExportStrategy):
    def export(self, data: dict) -> str:
        sep = "=" * 60
        lines = [sep, "  INFORME DE ADMINISTRACIÓN DE RESIDUOS", sep]

        def _write(d, indent=0):
            prefix = "  " * indent
            for k, v in d.items():
                if isinstance(v, dict):
                    lines.append(f"{prefix}[{k.upper()}]")
                    _write(v, indent + 1)
                elif isinstance(v, list):
                    lines.append(f"{prefix}[{k.upper()}]")
                    for item in v:
                        lines.append(f"{prefix}  - {item}")
                else:
                    lines.append(f"{prefix}{k}: {v}")

        _write(data)
        lines.append(sep)
        return "\n".join(lines)


class ExportContext:
    """Contexto del patrón Strategy; delega en la estrategia inyectada."""

    _strategies = {
        "json": JsonExportStrategy,
        "xml":  XmlExportStrategy,
        "txt":  TxtExportStrategy,
    }

    def __init__(self, formato: str = "json"):
        cls = self._strategies.get(formato, JsonExportStrategy)
        self._strategy = cls()

    def export(self, data: dict) -> str:
        return self._strategy.export(data)


# ══════════════════════════════════════════════════════════════════════════════
# SERVICIO PRINCIPAL DE ADMINISTRACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class AdministracionService:
    """
    Orquesta el flujo del Módulo 2:
    resultado_json → Grammar Engine → materiales → cola de prioridad → alertas.
    """

    def procesar_residuo(self, residuo) -> dict:
        resultado_json = residuo.resultado_json or {}
        objetos = resultado_json.get("objetos", {})
        total   = resultado_json.get("total", resultado_json.get("cantidad_total", 0))

        if not objetos:
            return {
                "materiales":              {},
                "material_predominante":   "Sin clasificar",
                "prioridad":               "Baja",
                "nivel_prioridad":         6,
                "peso_medio_kg":           0.0,
                "peso_medio_por_material": {},
                "alertas":                 ["Sin detecciones en esta imagen"],
                "resultado_grammar":       {"input": {}, "clasificaciones": [], "materiales": {}},
            }

        classifier      = MaterialClassifierFactory.create("grammar")
        materiales      = defaultdict(int)
        # peso ponderado: suma(peso_medio_kg × cantidad) por material
        peso_sum        = defaultdict(float)
        clasificaciones = []

        for objeto, cantidad in objetos.items():
            cant   = int(cantidad)
            result = classifier.classify(objeto, cant)
            material  = result.get("material", "Otro")
            peso_unit = float(result.get("peso_medio_kg", 0.0))
            materiales[material]   += cant
            peso_sum[material]     += peso_unit * cant
            clasificaciones.append(result)

        material_predominante = max(materiales, key=lambda k: materiales[k]) if materiales else "Otro"

        # Peso medio ponderado por material: suma(peso×cant) / suma(cant)
        peso_medio_por_material = {
            mat: round(peso_sum[mat] / materiales[mat], 4)
            for mat in materiales if materiales[mat] > 0
        }

        # Prioridad basada en el material predominante
        prioridad_nombre = MATERIAL_PRIORITY_LABEL.get(material_predominante, "Baja")
        nivel_prioridad  = MATERIAL_PRIORITY_LEVEL.get(material_predominante, 6)

        # Peso medio del material predominante (para guardarlo en el modelo)
        peso_medio_kg = peso_medio_por_material.get(material_predominante, 0.0)

        # Generación de alertas
        alertas = []
        if total > 20:
            alertas.append(f"Alta cantidad detectada: {total} objetos en una sola muestra")
        for mat, count in materiales.items():
            if mat == "Metal" and count >= 5:
                alertas.append(f"Metal reciclable: {count} unidades detectadas – recolectar pronto")
            if mat == "Vidrio" and count >= 3:
                alertas.append(f"Vidrio frágil: {count} unidades – manejar con protección")
            if mat == "Orgánico" and count > 0:
                alertas.append(f"Residuo orgánico: {count} unidades – requiere manejo inmediato")
            if mat == "Espuma/EPS" and count >= 2:
                alertas.append(f"Espuma/EPS: {count} unidades – material de difícil reciclaje")

        resultado_grammar = {
            "grammar_aplicada":       list(GRAMMAR_MODULO2.keys()),
            "reglas_totales":         len(MATERIAL_RULES),
            "input":                  {"objetos": objetos, "total": total},
            "clasificaciones":        clasificaciones,
            "materiales":             dict(materiales),
            "peso_medio_por_material": peso_medio_por_material,
            "material_predominante":  material_predominante,
            "prioridad":              prioridad_nombre,
        }

        return {
            "materiales":              dict(materiales),
            "material_predominante":   material_predominante,
            "prioridad":               prioridad_nombre,
            "nivel_prioridad":         nivel_prioridad,
            "peso_medio_kg":           peso_medio_kg,
            "peso_medio_por_material": peso_medio_por_material,
            "alertas":                 alertas,
            "resultado_grammar":       resultado_grammar,
        }

    def construir_cola_prioridad(self, pares_residuo_admin: list) -> list:
        """
        Devuelve los elementos ordenados por prioridad usando queue.PriorityQueue.
        Cada par es (residuo, admin_o_None).
        Retorna lista ordenada de dicts listos para mostrar en plantilla.
        """
        pq = queue.PriorityQueue()
        for residuo, admin in pares_residuo_admin:
            nivel = admin.nivel_prioridad if admin else 6
            pq.put((nivel, residuo.id, residuo, admin))

        resultado = []
        while not pq.empty():
            nivel, rid, residuo, admin = pq.get()
            resultado.append({
                "nivel":      nivel,
                "residuo":    residuo,
                "admin":      admin,
                "color":      PRIORITY_COLORS.get(admin.prioridad if admin else "", "secondary"),
                "mat_color":  MATERIAL_COLORS.get(admin.material_predominante if admin else "", "secondary"),
            })
        return resultado

    def exportar(self, formato: str, data: dict) -> str:
        ctx = ExportContext(formato)
        return ctx.export(data)


# ══════════════════════════════════════════════════════════════════════════════
# HILO DE PROCESAMIENTO EN SEGUNDO PLANO
# ══════════════════════════════════════════════════════════════════════════════

_lock   = threading.Lock()
_estado = {"running": False, "total": 0, "done": 0, "errores": 0}


def _worker_procesar(ids_residuos: list):
    """
    Hilo de trabajo: procesa residuos pendientes a través de Grammar Engine
    sin bloquear la interfaz de usuario.
    """
    from .models import Residuo, ResultadoAdministracion  # import tardío para evitar ciclos

    global _estado
    service = AdministracionService()

    with _lock:
        _estado = {"running": True, "total": len(ids_residuos), "done": 0, "errores": 0}

    try:
        for rid in ids_residuos:
            try:
                residuo   = Residuo.objects.get(pk=rid)
                resultado = service.procesar_residuo(residuo)

                ResultadoAdministracion.objects.update_or_create(
                    residuo=residuo,
                    defaults={
                        "material_predominante": resultado["material_predominante"],
                        "materiales":            resultado["materiales"],
                        "prioridad":             resultado["prioridad"],
                        "nivel_prioridad":       resultado["nivel_prioridad"],
                        "peso_medio_kg":         resultado["peso_medio_kg"],
                        "alertas":               resultado["alertas"],
                        "resultado_grammar":     resultado["resultado_grammar"],
                    },
                )

                # Actualizar categoría solo si sigue en "Pendiente"
                if residuo.categoria in ("Pendiente", ""):
                    residuo.categoria = resultado["material_predominante"]
                    residuo.save(update_fields=["categoria"])

            except Exception as exc:
                logger.error("Error procesando residuo #%s en worker: %s", rid, exc, exc_info=True)
                with _lock:
                    _estado["errores"] += 1

            with _lock:
                _estado["done"] += 1

    finally:
        with _lock:
            _estado["running"] = False


def iniciar_hilo_procesamiento(ids: list) -> threading.Thread:
    t = threading.Thread(target=_worker_procesar, args=(ids,), daemon=True)
    t.start()
    return t


def get_estado_procesamiento() -> dict:
    with _lock:
        return dict(_estado)

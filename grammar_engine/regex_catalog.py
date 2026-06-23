import re

# Patrones compilados reutilizables
EMAIL = re.compile(r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$')
TELEFONO = re.compile(r'^\+?[\d\s\-()\[\]]{7,15}$')
FECHA_ISO = re.compile(r'^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$')
NUMERO_POSITIVO = re.compile(r'^\d+(\.\d+)?$')
SOLO_LETRAS = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$')
NOMBRE_OBJETO = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s/\-]+$')
CANTIDAD_VALIDA = re.compile(r'^(0|[1-9]\d{0,4})$')   # 0–99999
MATERIAL_VALIDO = re.compile(
    r'^(Metal|Vidrio|Plástico|Papel\/Cartón|Orgánico|Espuma\/EPS|Otro)$'
)


def validar_patron(valor, patron: re.Pattern, descripcion: str = "valor") -> bool:
    texto = str(valor)
    if not patron.match(texto):
        raise ValueError(
            f"El {descripcion} '{texto}' no tiene el formato esperado."
        )
    return True


def extraer_numeros(texto: str) -> list:
    return [
        int(n) if '.' not in n else float(n)
        for n in re.findall(r'-?\d+\.?\d*', texto)
    ]


def extraer_palabras_clave(texto: str, palabras: list) -> list:
    if not palabras:
        return []
    patron = re.compile(
        r'\b(' + '|'.join(re.escape(p) for p in palabras) + r')\b',
        re.IGNORECASE,
    )
    return patron.findall(texto)


def limpiar_texto(texto: str) -> str:
    texto = re.sub(r'\s+', ' ', texto)
    texto = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ/\-]', '', texto)
    return texto.strip()

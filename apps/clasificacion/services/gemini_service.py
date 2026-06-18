import google.generativeai as genai
from PIL import Image
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

_PROMPT = """
Analiza cuidadosamente la imagen de residuos.

Reglas estrictas:
- Cuenta SOLO objetos claramente visibles y reconocibles.
- Si un objeto está borroso, cortado, tapado, muy pequeño o dudoso, NO lo cuentes.
- Prefiere NO contar antes que contar de más.
- No inventes objetos que no se vean con alta seguridad.
- No repitas objetos por reflejos, sombras, etiquetas o partes parciales.
- Si no estás seguro de una clase, omítela.
- Cuenta únicamente lo obvio y visible.

Devuelve SOLO JSON válido, sin texto extra, sin explicaciones, sin markdown.

Formato exacto:
{
  "objetos": {
    "botella": 8,
    "lata": 3
  }
}

Si no detectas objetos con seguridad, devuelve:
{
  "objetos": {}
}
"""


def analizar_residuos_gemini(ruta_imagen: str) -> str:
    imagen = Image.open(ruta_imagen)
    respuesta = model.generate_content([_PROMPT, imagen])
    return respuesta.text

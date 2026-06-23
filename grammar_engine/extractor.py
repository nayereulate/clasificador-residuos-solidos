import re


class Extractor:

    @staticmethod
    def extract(data, fields):
        result = {}
        for field in fields:
            if field in data:
                result[field] = data[field]
        return result

    @staticmethod
    def remove(data, fields):
        result = data.copy()
        for field in fields:
            if field in result:
                del result[field]
        return result

    @staticmethod
    def extract_from_text(text: str, fields: list, pattern_map: dict = None) -> dict:
        """
        Extrae campos de texto libre usando regex.

        pattern_map: dict {field: regex_pattern} con grupos nombrados opcionales.
        Si no se provee patrón para un campo, intenta 'campo: valor' o 'campo=valor'.
        """
        result = {}
        pattern_map = pattern_map or {}

        for field in fields:
            if field in pattern_map:
                match = re.search(pattern_map[field], text, re.IGNORECASE)
                if match:
                    try:
                        result[field] = match.group("value")
                    except IndexError:
                        result[field] = match.group(0)
            else:
                # Patrón genérico: campo: valor o campo=valor
                generic = re.search(
                    rf'{re.escape(field)}\s*[:=]\s*([^\n,;]+)',
                    text,
                    re.IGNORECASE,
                )
                if generic:
                    result[field] = generic.group(1).strip()

        return result

    @staticmethod
    def extract_numbers(text: str) -> list:
        """Extrae todos los números (int o float) de un texto."""
        return [
            int(n) if '.' not in n else float(n)
            for n in re.findall(r'-?\d+\.?\d*', text)
        ]

    @staticmethod
    def extract_keywords(text: str, keywords: list) -> list:
        """Extrae palabras clave presentes en el texto (búsqueda por límite de palabra)."""
        if not keywords:
            return []
        patron = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b',
            re.IGNORECASE,
        )
        return patron.findall(text)

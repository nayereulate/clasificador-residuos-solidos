import re
import json
import xml.etree.ElementTree as ET


class Parser:
    # Detectores de formato
    _RE_JSON = re.compile(r'^\s*[\[{]')
    _RE_XML = re.compile(r'^\s*<[a-zA-Z]')
    _RE_KEY_VALUE = re.compile(r'^([a-zA-Z_]\w*)\s*[:=]\s*(.+)$', re.MULTILINE)
    _RE_NUMBER = re.compile(r'^-?\d+(\.\d+)?$')
    _RE_BOOL = re.compile(r'^(true|false|yes|no|sí|si)$', re.IGNORECASE)

    @classmethod
    def parse(cls, data):
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            return cls._parse_string(data)
        raise TypeError(f"Formato no soportado: {type(data).__name__}")

    @classmethod
    def _parse_string(cls, text):
        text = text.strip()
        if cls._RE_JSON.match(text):
            return cls._parse_json(text)
        if cls._RE_XML.match(text):
            return cls._parse_xml(text)
        return cls._parse_key_value(text)

    @classmethod
    def _parse_json(cls, text):
        try:
            result = json.loads(text)
            return result if isinstance(result, dict) else {"data": result}
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido: {e}")

    @classmethod
    def _parse_xml(cls, text):
        try:
            root = ET.fromstring(text)
            return cls._xml_to_dict(root)
        except ET.ParseError as e:
            raise ValueError(f"XML inválido: {e}")

    @classmethod
    def _xml_to_dict(cls, element):
        result = {}
        for child in element:
            val = cls._xml_to_dict(child) if len(child) else (child.text or "")
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(val)
            else:
                result[child.tag] = val
        return result

    @classmethod
    def _parse_key_value(cls, text):
        result = {}
        for match in cls._RE_KEY_VALUE.finditer(text):
            key = match.group(1).strip()
            val = match.group(2).strip()
            result[key] = cls._coerce_value(val)
        if not result:
            raise ValueError(
                f"No se pudo parsear como clave=valor: {text[:50]!r}"
            )
        return result

    @classmethod
    def _coerce_value(cls, val):
        if cls._RE_NUMBER.match(val):
            return int(val) if '.' not in val else float(val)
        if cls._RE_BOOL.match(val):
            return val.lower() in ('true', 'yes', 'sí', 'si')
        return val.strip('"\'')

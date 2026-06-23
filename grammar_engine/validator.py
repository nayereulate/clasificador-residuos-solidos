import re

from .exceptions import ValidationError


class Validator:

    @staticmethod
    def validate(data: dict, grammar: dict) -> bool:

        if not isinstance(data, dict):
            raise ValidationError("La estructura debe ser un diccionario.")

        for field, rules in grammar.items():

            # Permitir nulo explícitamente
            nullable = rules.get("nullable", False)

            # Campo obligatorio
            if rules.get("required", False):
                if field not in data:
                    raise ValidationError(
                        f"Campo obligatorio faltante: '{field}'"
                    )

            if field not in data:
                continue

            value = data[field]

            # Nullable: si el valor es None y el campo lo permite, saltar
            if value is None:
                if nullable:
                    continue
                raise ValidationError(
                    f"El campo '{field}' no puede ser nulo."
                )

            # Strip antes de validar (solo strings)
            if rules.get("strip", False) and isinstance(value, str):
                value = value.strip()
                data[field] = value

            # Tipo esperado
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                raise ValidationError(
                    f"El campo '{field}' recibió '{value}' "
                    f"({type(value).__name__}): se esperaba "
                    f"{expected_type.__name__}."
                )

            # Valores permitidos
            allowed_values = rules.get("values")
            if allowed_values and value not in allowed_values:
                raise ValidationError(
                    f"El campo '{field}' recibió '{value}': "
                    f"valores permitidos: {allowed_values}."
                )

            # Mínimo (numérico)
            minimum = rules.get("min")
            if minimum is not None and value < minimum:
                raise ValidationError(
                    f"El campo '{field}' recibió '{value}': "
                    f"debe ser >= {minimum}."
                )

            # Máximo (numérico)
            maximum = rules.get("max")
            if maximum is not None and value > maximum:
                raise ValidationError(
                    f"El campo '{field}' recibió '{value}': "
                    f"debe ser <= {maximum}."
                )

            # Longitud mínima (strings)
            min_length = rules.get("min_length")
            if min_length is not None and isinstance(value, str):
                if len(value) < min_length:
                    raise ValidationError(
                        f"El campo '{field}' recibió '{value}': "
                        f"longitud mínima {min_length} caracteres."
                    )

            # Longitud máxima (strings)
            max_length = rules.get("max_length")
            if max_length is not None and isinstance(value, str):
                if len(value) > max_length:
                    raise ValidationError(
                        f"El campo '{field}' recibió '{value}': "
                        f"longitud máxima {max_length} caracteres."
                    )

            # Patrón regex (strings)
            pattern = rules.get("pattern")
            if pattern and isinstance(value, str):
                if not re.fullmatch(pattern, value):
                    msg = rules.get("pattern_msg", f"no coincide con el patrón requerido")
                    raise ValidationError(
                        f"El campo '{field}' recibió '{value}': {msg}."
                    )

        return True

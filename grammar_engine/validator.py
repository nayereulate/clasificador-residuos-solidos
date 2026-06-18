from .exceptions import ValidationError


class Validator:

    @staticmethod
    def validate(data: dict, grammar: dict) -> bool:

        if not isinstance(data, dict):
            raise ValidationError(
                "La estructura debe ser un diccionario."
            )

        for field, rules in grammar.items():

            # Campo obligatorio
            if rules.get("required", False):

                if field not in data:
                    raise ValidationError(
                        f"Campo obligatorio faltante: {field}"
                    )

            # Si no existe y no es obligatorio
            if field not in data:
                continue

            value = data[field]

            # Tipo esperado
            expected_type = rules.get("type")

            if expected_type:

                if not isinstance(value, expected_type):

                    raise ValidationError(
                        f"El campo '{field}' debe ser "
                        f"{expected_type.__name__}"
                    )

            # Valores permitidos
            allowed_values = rules.get("values")

            if allowed_values:

                if value not in allowed_values:

                    raise ValidationError(
                        f"Valor inválido en '{field}'. "
                        f"Permitidos: {allowed_values}"
                    )

            # Mínimo
            minimum = rules.get("min")

            if minimum is not None:

                if value < minimum:

                    raise ValidationError(
                        f"'{field}' debe ser >= {minimum}"
                    )

            # Máximo
            maximum = rules.get("max")

            if maximum is not None:

                if value > maximum:

                    raise ValidationError(
                        f"'{field}' debe ser <= {maximum}"
                    )

        return True
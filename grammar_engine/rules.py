from .exceptions import RuleError


class RuleEngine:

    @staticmethod
    def match_condition(data, condition):

        for key, expected_value in condition.items():

            if key not in data:
                return False

            if data[key] != expected_value:
                return False

        return True

    @staticmethod
    def apply(data, rules):

        result = data.copy()

        for rule in rules:

            condition = rule.get("if", {})
            action = rule.get("then", {})

            if RuleEngine.match_condition(
                result,
                condition
            ):
                result.update(action)

        return result
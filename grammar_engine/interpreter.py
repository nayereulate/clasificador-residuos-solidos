from .rules import RuleEngine

class Interpreter:

    @staticmethod
    def interpret(data, rules):

        result = RuleEngine.apply(
            data,
            rules
        )

        return result
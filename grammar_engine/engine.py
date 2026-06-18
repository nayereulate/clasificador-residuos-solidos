from .validator import Validator
from .interpreter import Interpreter
from .extractor import Extractor
from .transformer import Transformer
from .parser import Parser

class GrammarEngine:

    def validate(
        self,
        data,
        grammar
    ):
        return Validator.validate(
            data,
            grammar
        )

    def interpret(
        self,
        data,
        rules
    ):
        return Interpreter.interpret(
            data,
            rules
        )

    def extract(
        self,
        data,
        fields
    ):
        return Extractor.extract(
            data,
            fields
        )

    def transform_to_json(
        self,
        data
    ):
        return Transformer.dict_to_json(
            data
        )

    def transform_to_xml(
        self,
        data
    ):
        return Transformer.dict_to_xml(
            data
        )

    def process(
        self,
        data,
        grammar,
        rules
    ):

        parsed = Parser.parse(data)

        Validator.validate(
            parsed,
            grammar
        )

        result = Interpreter.interpret(
            parsed,
            rules
        )

        return result
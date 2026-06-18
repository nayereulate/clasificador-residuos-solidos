from engine import GrammarEngine

from examples.residuo_grammar import GRAMMAR
from examples.residuo_rules import RULES


engine = GrammarEngine()

datos = {
    "tipo": "botella",
    "cantidad": 20,
    "estado": "limpia"
}

resultado = engine.process(
    datos,
    GRAMMAR,
    RULES
)

print("Resultado:")
print(resultado)

print()

print("JSON:")
print(
    engine.transform_to_json(
        resultado
    )
)

print()

print("XML:")
print(
    engine.transform_to_xml(
        resultado
    )
)
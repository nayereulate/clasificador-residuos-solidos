class Parser:

    @staticmethod
    def parse(data):

        if isinstance(data, dict):
            return data

        raise TypeError(
            "Formato no soportado por el parser."
        )
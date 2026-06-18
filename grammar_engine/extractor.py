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
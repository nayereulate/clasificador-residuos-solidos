import json


class JSONAdapter:

    @staticmethod
    def load(json_string):

        return json.loads(json_string)

    @staticmethod
    def dump(data):

        return json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )
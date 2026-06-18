import json
import xml.etree.ElementTree as ET


class Transformer:

    @staticmethod
    def dict_to_json(data):

        return json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )

    @staticmethod
    def json_to_dict(json_string):

        return json.loads(json_string)

    @staticmethod
    def dict_to_xml(data, root_name="root"):

        root = ET.Element(root_name)

        for key, value in data.items():

            child = ET.SubElement(
                root,
                key
            )

            child.text = str(value)

        return ET.tostring(
            root,
            encoding="unicode"
        )

    @staticmethod
    def xml_to_dict(xml_string):

        root = ET.fromstring(xml_string)

        result = {}

        for child in root:

            result[child.tag] = child.text

        return result
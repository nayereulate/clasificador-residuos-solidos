import xml.etree.ElementTree as ET


class XMLAdapter:

    @staticmethod
    def load(xml_string):

        root = ET.fromstring(
            xml_string
        )

        result = {}

        for child in root:

            result[child.tag] = child.text

        return result

    @staticmethod
    def dump(
        data,
        root_name="root"
    ):

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
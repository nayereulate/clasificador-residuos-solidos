GRAMMAR = {

    "tipo": {
        "required": True,
        "type": str,
        "values": [
            "botella",
            "papel",
            "vidrio"
        ]
    },

    "cantidad": {
        "required": True,
        "type": int,
        "min": 1
    },

    "estado": {
        "required": True,
        "type": str,
        "values": [
            "limpia",
            "sucia"
        ]
    }

}
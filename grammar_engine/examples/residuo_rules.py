RULES = [

    {
        "if": {
            "tipo": "botella"
        },
        "then": {
            "categoria": "plastico"
        }
    },

    {
        "if": {
            "categoria": "plastico"
        },
        "then": {
            "reciclable": True
        }
    }

]
import re

from didi.food import norm

EXACT = {
    "help": {"ayuda", "help", "start", "comandos", "hola", "buenas", "buen dia"},
    "list": {
        "lista",
        "ver lista",
        "que falta",
        "que hay que comprar",
        "mostrar lista",
        "que tenemos que comprar",
    },
    "clear_bought": {"limpiar", "limpiar comprados", "borrar comprados"},
    "clear_pending": {
        "vaciar lista",
        "vaciar la lista",
        "vaciar",
        "borrar lista",
        "borrar la lista",
        "borrar todo",
        "borrar toda la lista",
        "borra la lista",
        "borra todo",
        "eliminar lista",
        "eliminar la lista",
        "eliminar todo",
        "eliminar toda la lista",
        "elimina la lista",
        "elimina todo",
        "limpiar lista",
        "limpiar la lista",
        "sacar la lista",
        "sacar todo",
        "saca la lista",
        "saca todo",
    },
    "leave": {"salir", "irme", "dejar la lista"},
    "buy_all": {
        "ya compramos todo",
        "compramos todo",
        "ya compre todo",
        "compre todo",
        "ya esta todo",
        "ya esta todo comprado",
    },
    "buy_smart": {
        "ya lo compramos",
        "ya la compramos",
        "ya los compramos",
        "ya las compramos",
        "ya esta comprado",
        "ya esta comprada",
    },
}

ADD_PREFIXES = [
    ["tenemos", "que", "comprar"],
    ["hay", "que", "comprar"],
    ["agregame"],
    ["agregar"],
    ["agrega"],
    ["comprame"],
    ["comprar"],
    ["compra"],
    ["sumame"],
    ["sumar"],
    ["suma"],
    ["anotame"],
    ["anotar"],
    ["anota"],
    ["necesitamos"],
    ["necesito"],
    ["faltan"],
    ["falta"],
    ["poneme"],
    ["poner"],
    ["pone"],
]

REMOVE_PREFIXES = [
    ["ya", "no", "hace", "falta"],
    ["ya", "no", "necesitamos"],
    ["eliminame"],
    ["eliminar"],
    ["elimina"],
    ["borrame"],
    ["borrar"],
    ["borra"],
    ["sacame"],
    ["sacar"],
    ["saca"],
    ["quitar"],
    ["quita"],
]

BUY_PREFIXES = [
    ["ya", "esta", "comprado"],
    ["ya", "esta", "comprada"],
    ["marcar", "como", "comprado"],
    ["ya", "compramos"],
    ["ya", "compre"],
    ["compramos"],
    ["compre"],
    ["marcar"],
    ["marcame"],
    ["marca"],
]

COMMAND = re.compile(r"^/([a-zA-Z_]+)(?:@\w+)?(?:\s+([\s\S]+))?$")
PICK = re.compile(r"^(?:receta|la|numero|num|ver)?\s*(\d{1,2})$")
SPLIT = re.compile(r",|\s+y\s+|\s+e\s+", re.IGNORECASE)
ARTICLE = re.compile(r"^(el|la|los|las|un|una|unos|unas)\s+", re.IGNORECASE)


def split_items(raw):
    parts = SPLIT.split(str(raw))
    items = []
    for part in parts:
        cleaned = ARTICLE.sub("", part).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _words(text):
    pairs = []
    for raw in text.strip().split():
        normalized = norm(raw)
        if normalized:
            pairs.append({"raw": raw, "n": normalized})
    return pairs


def _match_prefix(words, prefixes):
    ordered = sorted(prefixes, key=len, reverse=True)
    for prefix in ordered:
        if len(words) <= len(prefix):
            continue
        if all(words[index]["n"] == part for index, part in enumerate(prefix)):
            return len(prefix)
    return 0


def _with_items(kind, pairs, prefix_length):
    raw = " ".join(word["raw"] for word in pairs[prefix_length:])
    return {"type": kind, "items": split_items(raw)}


def _from_command(raw):
    match = COMMAND.match(raw)
    if not match:
        return raw
    command = match.group(1).lower()
    arg = (match.group(2) or "").strip()
    mapped = {
        "start": "ayuda",
        "help": "ayuda",
        "ayuda": "ayuda",
        "lista": "lista",
        "list": "lista",
        "limpiar": "limpiar",
        "vaciar": "vaciar lista",
        "salir": "salir",
        "agregar": f"agrega {arg}" if arg else "agrega",
        "add": f"agrega {arg}" if arg else "agrega",
        "comprar": f"compra {arg}" if arg else "compra",
        "sacar": f"saca {arg}" if arg else "saca",
        "borrar": f"saca {arg}" if arg else "saca",
        "compre": f"ya compre {arg}" if arg else "ya compre",
    }
    return mapped.get(command, raw)


def parse(value):
    raw = _from_command(str(value or "").strip())
    normalized = norm(raw)
    if not normalized:
        return {"type": "unknown"}
    for kind in ("help", "list", "clear_bought", "clear_pending", "leave", "buy_all", "buy_smart"):
        if normalized in EXACT[kind]:
            return {"type": kind}

    pick = PICK.match(normalized)
    if pick and normalized != pick.group(1):
        return {"type": "pick", "n": int(pick.group(1))}
    if re.fullmatch(r"\d{1,2}", normalized):
        return {"type": "pick", "n": int(normalized)}

    pairs = _words(raw)
    add_length = _match_prefix(pairs, ADD_PREFIXES)
    if add_length:
        return _with_items("add", pairs, add_length)
    remove_length = _match_prefix(pairs, REMOVE_PREFIXES)
    if remove_length:
        return _with_items("remove", pairs, remove_length)
    buy_length = _match_prefix(pairs, BUY_PREFIXES)
    if buy_length:
        return _with_items("buy", pairs, buy_length)

    if normalized in {"agrega", "agregar", "comprar", "compra"}:
        return {"type": "add", "items": []}
    if normalized in {"saca", "sacar"}:
        return {"type": "remove", "items": []}
    if normalized in {"ya compre", "compre", "compramos"}:
        return {"type": "buy", "items": []}

    return {"type": "unknown"}

import re
import unicodedata

UNIT = (
    r"kg|kilos?|g|grs?|gramos|mg|l|lts?|litros?|ml|cc|unidades?|unid|"
    r"paquetes?|paq|latas?|docenas?|manojos?|atados?|sachet|sobres?"
)
QTY_WORD = r"\d+(?:[.,]\d+)?|medio|media|unos|unas|un|una|dos|tres|cuatro|cinco|seis|doce"
QTY = rf"(?:{QTY_WORD})(?:\s+(?:{UNIT}))?"
QTY_START = re.compile(rf"^(?:{QTY}\s+)+(?:de\s+)?", re.IGNORECASE)
QTY_END = re.compile(rf"(?:\s+{QTY})+$", re.IGNORECASE)
LEADING = re.compile(r"^(?:(?:de|del|la|el|los|las)\s+)+")

NON_FOOD = {
    "detergente",
    "lavandina",
    "cloro",
    "jabon",
    "shampoo",
    "shampu",
    "acondicionador",
    "desodorante",
    "dentifrico",
    "esponja",
    "virulana",
    "suavizante",
    "lavavajilla",
    "lavavajillas",
    "desengrasante",
    "limpiavidrios",
    "insecticida",
    "desinfectante",
    "servilleta",
    "servilletas",
    "panuelo",
    "panuelos",
    "toallita",
    "toallitas",
    "panal",
    "panales",
    "algodon",
    "hisopo",
    "hisopos",
    "fosforo",
    "fosforos",
    "pila",
    "pilas",
    "lamparita",
    "foco",
    "escoba",
    "trapo",
    "rejilla",
    "lysoform",
    "procenex",
    "glade",
    "curita",
    "curitas",
    "ibuprofeno",
    "paracetamol",
    "preservativo",
    "preservativos",
    "residuo",
    "residuos",
    "higienico",
    "mascota",
    "whiskas",
    "purina",
}

NON_FOOD_PHRASES = [
    "papel higienico",
    "papel de cocina",
    "bolsa de residuos",
    "bolsas de residuos",
    "rollo de cocina",
    "alcohol en gel",
    "jabon en polvo",
    "alimento para perro",
    "alimento para gato",
    "arena para gato",
    "arena para gatos",
]

FOOD_PHRASES = [
    ("dulce de leche", "ddl"),
    ("pata muslo", "pollo"),
    ("filet de merluza", "pescado"),
    ("filet de pescado", "pescado"),
    ("filet de pollo", "pollo"),
    ("salsa de tomate", "tomate"),
    ("pure de tomate", "tomate"),
    ("jugo de naranja", "naranja"),
    ("jugo de limon", "limon"),
]

WORDS = {
    "pollo": "pollo",
    "pechuga": "pollo",
    "pechugas": "pollo",
    "suprema": "pollo",
    "supremas": "pollo",
    "muslo": "pollo",
    "muslos": "pollo",
    "alitas": "pollo",
    "alita": "pollo",
    "carne": "carne",
    "nalga": "carne",
    "cuadril": "carne",
    "vacio": "carne",
    "asado": "carne",
    "bife": "carne",
    "bifes": "carne",
    "matambre": "carne",
    "hamburguesa": "carne",
    "hamburguesas": "carne",
    "cerdo": "cerdo",
    "bondiola": "cerdo",
    "chuleta": "cerdo",
    "chuletas": "cerdo",
    "chorizo": "cerdo",
    "chorizos": "cerdo",
    "salchicha": "cerdo",
    "salchichas": "cerdo",
    "pescado": "pescado",
    "merluza": "pescado",
    "salmon": "pescado",
    "lenguado": "pescado",
    "atun": "atun",
    "caballa": "atun",
    "huevo": "huevo",
    "huevos": "huevo",
    "arroz": "arroz",
    "fideo": "fideo",
    "fideos": "fideo",
    "spaghetti": "fideo",
    "espagueti": "fideo",
    "tallarines": "fideo",
    "tallarin": "fideo",
    "mostachol": "fideo",
    "mostacholes": "fideo",
    "penne": "fideo",
    "tirabuzones": "fideo",
    "papa": "papa",
    "papas": "papa",
    "tomate": "tomate",
    "tomates": "tomate",
    "cebolla": "cebolla",
    "cebollas": "cebolla",
    "queso": "queso",
    "quesos": "queso",
    "muzzarella": "queso",
    "mozzarella": "queso",
    "muzza": "queso",
    "leche": "leche",
    "lenteja": "lenteja",
    "lentejas": "lenteja",
    "yogur": "yogur",
    "yogurt": "yogur",
    "yogures": "yogur",
    "pan": "pan",
    "lactal": "pan",
    "lechuga": "lechuga",
    "lechugas": "lechuga",
    "zanahoria": "zanahoria",
    "zanahorias": "zanahoria",
    "morron": "morron",
    "morrones": "morron",
    "pimiento": "morron",
    "pimientos": "morron",
    "choclo": "choclo",
    "choclos": "choclo",
    "limon": "limon",
    "limones": "limon",
    "jamon": "jamon",
    "jamones": "jamon",
    "crema": "crema",
    "manteca": "manteca",
    "espinaca": "espinaca",
    "espinacas": "espinaca",
    "harina": "harina",
    "banana": "banana",
    "bananas": "banana",
    "frutilla": "frutilla",
    "frutillas": "frutilla",
    "avena": "avena",
    "miel": "miel",
    "chocolate": "chocolate",
    "pepino": "pepino",
    "pepinos": "pepino",
    "batata": "batata",
    "batatas": "batata",
    "zapallo": "zapallo",
    "zapallos": "zapallo",
    "palta": "palta",
    "paltas": "palta",
    "aguacate": "palta",
    "manzana": "manzana",
    "manzanas": "manzana",
    "garbanzo": "garbanzo",
    "garbanzos": "garbanzo",
    "poroto": "poroto",
    "porotos": "poroto",
    "perejil": "perejil",
    "naranja": "naranja",
    "naranjas": "naranja",
    "ajo": "ajo",
    "ajos": "ajo",
}

LABEL = {
    "pollo": "pollo",
    "carne": "carne",
    "cerdo": "cerdo",
    "pescado": "pescado",
    "atun": "atún",
    "huevo": "huevos",
    "arroz": "arroz",
    "fideo": "fideos",
    "papa": "papas",
    "tomate": "tomate",
    "cebolla": "cebolla",
    "queso": "queso",
    "leche": "leche",
    "lenteja": "lentejas",
    "yogur": "yogur",
    "pan": "pan",
    "lechuga": "lechuga",
    "zanahoria": "zanahoria",
    "morron": "morrón",
    "choclo": "choclo",
    "limon": "limón",
    "jamon": "jamón",
    "crema": "crema",
    "manteca": "manteca",
    "espinaca": "espinaca",
    "harina": "harina",
    "banana": "banana",
    "frutilla": "frutillas",
    "avena": "avena",
    "miel": "miel",
    "chocolate": "chocolate",
    "pepino": "pepino",
    "batata": "batata",
    "zapallo": "zapallo",
    "palta": "palta",
    "manzana": "manzana",
    "garbanzo": "garbanzos",
    "poroto": "porotos",
    "perejil": "perejil",
    "ddl": "dulce de leche",
    "naranja": "naranja",
    "ajo": "ajo",
}


def label(key):
    return LABEL.get(key, key)


def norm(value):
    text = unicodedata.normalize("NFD", str(value).lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_name(value):
    text = norm(value)
    text = QTY_START.sub("", text)
    text = QTY_END.sub("", text)
    text = LEADING.sub("", text)
    return text.strip()


def keywords(value):
    text = norm(value)
    found = {}
    for phrase, key in sorted(FOOD_PHRASES, key=lambda item: len(item[0]), reverse=True):
        if phrase in text:
            found[key] = True
            text = text.replace(phrase, " ")
    text = clean_name(text)
    tokens = {token for token in text.split(" ") if token}
    for word, key in WORDS.items():
        if word in tokens:
            found[key] = True
    return list(found)


def is_edible(value):
    text = norm(value)
    if any(phrase in text for phrase in NON_FOOD_PHRASES):
        return False
    tokens = {token for token in text.split(" ") if token}
    if tokens & NON_FOOD:
        return False
    container = bool(tokens & {"papel", "rollo", "bolsa", "bolsas"})
    if container and not keywords(value):
        return False
    return True


def pretty(value):
    text = re.sub(r"\s+", " ", str(value).strip())
    if not text:
        return ""
    return text[0].upper() + text[1:]

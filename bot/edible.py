from __future__ import annotations

from bot.textutil import contains_phrase, normalize

# Frases de limpieza y hogar. "papel" solo no alcanza: el papel de arroz se come.
NON_EDIBLE = {
    "detergente",
    "jabon",
    "jabon en polvo",
    "shampoo",
    "acondicionador",
    "lavandina",
    "cloro",
    "cloro gel",
    "suavizante",
    "esponja",
    "virulana",
    "desengrasante",
    "lavalozas",
    "lavaloza",
    "lavavajillas",
    "insecticida",
    "desodorante",
    "pasta dental",
    "dentifrico",
    "cepillo",
    "cepillo de dientes",
    "toalla",
    "toallas",
    "toallon",
    "papel higienico",
    "papel aluminio",
    "papel de cocina",
    "papel manteca",
    "rollo de cocina",
    "servilleta",
    "servilletas",
    "panuelo",
    "panuelos",
    "algodon",
    "hisopo",
    "hisopos",
    "panal",
    "panales",
    "bolsa",
    "bolsas",
    "bolsas de basura",
    "aluminio",
    "film",
    "film adherente",
    "escoba",
    "trapo",
    "trapero",
    "rejilla",
    "guantes",
    "fosforo",
    "fosforos",
    "vela",
    "velas",
    "pila",
    "pilas",
    "ampolleta",
    "ampolletas",
    "foco",
    "bombilla",
    "quitamanchas",
    "perfume",
    "talco",
    "bloqueador",
    "protector solar",
    "confort",
    "esmalte",
    "acetona",
    "alcohol",
    "alcohol gel",
    "alcohol etilico",
    "desinfectante",
    "papel",
}
EDIBLE_EXCEPTIONS = {"papel de arroz"}

# Condimentos que aparecen en casi cualquier receta y no sirven para recomendar.
STAPLES = {
    "sal",
    "sal gruesa",
    "sal fina",
    "pimienta",
    "pimienta negra",
    "aceite",
    "aceite de oliva",
    "vinagre",
    "agua",
    "azucar",
    "azucar rubia",
    "harina",
    "comino",
    "oregano",
    "paprika",
    "pimenton dulce",
    "canela",
    "laurel",
    "curry",
    "aji molido",
    "provenzal",
    "nuez moscada",
    "clavo de olor",
    "bicarbonato",
    "polvo de hornear",
    "levadura",
    "caldo",
}


def is_edible(name: str) -> bool:
    normalized = normalize(name)
    if _matches(normalized, EDIBLE_EXCEPTIONS):
        return True
    if _matches(normalized, NON_EDIBLE):
        return False
    return True


def is_staple(name: str) -> bool:
    return _matches(normalize(name), STAPLES)


def wants_recipes(name: str) -> bool:
    return is_edible(name) and not is_staple(name)


def _matches(name: str, phrases: set[str]) -> bool:
    return any(contains_phrase(name, phrase) for phrase in phrases)

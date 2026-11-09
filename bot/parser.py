from __future__ import annotations

import re
from dataclasses import dataclass

from bot.textutil import normalize

HELP_EXACT = {
    "ayuda",
    "help",
    "start",
    "hola",
    "buenas",
    "buenas tardes",
    "buenos dias",
    "menu",
    "como funciona",
    "que podes hacer",
    "que puedes hacer",
}
LIST_EXACT = {
    "lista",
    "ver lista",
    "la lista",
    "mostrar lista",
    "que falta",
    "que hay",
    "que hay que comprar",
    "que falta comprar",
}
BUY_PREFIXES = (
    "ya estan comprados",
    "ya esta comprado",
    "ya los compre",
    "ya lo compre",
    "ya compramos",
    "ya compre",
    "compramos",
    "comprado",
    "comprada",
    "compre",
)
DELETE_PREFIXES = (
    "ya no hace falta",
    "no hace falta",
    "eliminar",
    "elimina",
    "borrar",
    "borra",
    "sacar",
    "saca",
    "quitar",
    "quita",
)
ADD_PREFIXES = (
    "hay que comprar",
    "falta comprar",
    "suma a la lista",
    "agregar a la lista",
    "anota que",
    "necesitamos",
    "necesito",
    "agregar",
    "agrega",
    "anadir",
    "anade",
    "anotar",
    "anota",
    "comprar",
    "compra",
    "faltan",
    "falta",
    "poneme",
    "sumar",
    "suma",
    "pone",
)
COMMANDS = {
    "start": "help",
    "ayuda": "help",
    "help": "help",
    "lista": "list",
    "list": "list",
    "agregar": "add",
    "anadir": "add",
    "add": "add",
    "compre": "buy",
    "compramos": "buy",
    "comprado": "buy",
    "comprar": "add",
    "borrar": "delete",
    "sacar": "delete",
    "eliminar": "delete",
    "delete": "delete",
}
ARTICLES = ("el ", "la ", "los ", "las ", "un ", "una ", "unos ", "unas ")
ALL_WORDS = {"todo", "toda", "todos", "todas", "toda la lista", "todo lo", "la lista"}
_DOCENA = re.compile(r"^(?:media\s+)?docenas?\s+de\s+", re.IGNORECASE)
_LOOSE_QTY = re.compile(
    r"^(?:kilos?|litros?|gramos?|latas?|botellas?|packs?)\s+de\s+",
    re.IGNORECASE,
)
_QTY = re.compile(
    r"^(?:\d+(?:[.,]\d+)?|dos|tres|cuatro|cinco|seis|medio|media)\s*"
    r"(?:kg|kilos|kilo|g|gr|gramos|l|lt|lts|litros|litro|ml|unidades|unidad|"
    r"pack|packs|latas|lata|botellas|botella|docena|docenas)?\s*"
    r"(?:de\s+)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Intent:
    kind: str
    items: tuple[str, ...]


def parse(text: str) -> Intent:
    raw = text.strip().strip("¿?¡!").strip()
    if not raw:
        return Intent("help", ())
    if raw.startswith("/"):
        return _parse_command(raw)

    normalized = normalize(raw)
    if normalized in LIST_EXACT:
        return Intent("list", ())
    if normalized in HELP_EXACT:
        return Intent("help", ())

    deleted = _consume(raw, DELETE_PREFIXES)
    if deleted is not None:
        return Intent("delete", tuple(split_items(deleted)))

    bought = _consume(raw, BUY_PREFIXES)
    if bought is not None:
        items = split_items(bought)
        return Intent("buy", tuple(items or ["*"]))

    added = _consume(raw, ADD_PREFIXES)
    if added is not None:
        return Intent("add", tuple(split_items(added)))

    if len(normalized.split()) > 12 and "," not in raw:
        return Intent("help", ())
    return Intent("add", tuple(split_items(raw)))


def split_items(text: str) -> list[str]:
    cleaned = text.strip(" :.-")
    if not cleaned:
        return []
    if normalize(cleaned) in ALL_WORDS:
        return ["*"]
    replaced = re.sub(r"\s+y\s+", ", ", cleaned, flags=re.IGNORECASE)
    replaced = re.sub(r"\s+e\s+", ", ", replaced, flags=re.IGNORECASE)
    items: list[str] = []
    for part in replaced.split(","):
        item = clean_item(part)
        if item and item != "*":
            items.append(item)
    return items


def clean_item(part: str) -> str:
    item = part.strip(" .;:¡!¿?")
    item = _strip_article(item)
    item = _strip_qty(item)
    item = _strip_article(item)
    item = _DOCENA.sub("", item, count=1).strip()
    item = _LOOSE_QTY.sub("", item, count=1).strip()
    return re.sub(r"\s+", " ", item).strip()


def _parse_command(raw: str) -> Intent:
    body = raw[1:]
    command, _, rest = body.partition(" ")
    command = normalize(command.split("@", 1)[0])
    kind = COMMANDS.get(command)
    if kind is None:
        return Intent("help", ())
    if kind in {"help", "list"}:
        return Intent(kind, ())
    items = split_items(rest)
    if kind == "buy":
        return Intent("buy", tuple(items or ["*"]))
    return Intent(kind, tuple(items))


def _consume(raw: str, prefixes: tuple[str, ...]) -> str | None:
    normalized = normalize(raw)
    for prefix in sorted(prefixes, key=len, reverse=True):
        if normalized == prefix or normalized.startswith(prefix + " "):
            return raw[len(prefix) :].strip()
    return None


def _strip_article(part: str) -> str:
    normalized = normalize(part)
    for article in ARTICLES:
        if normalized.startswith(article):
            return part[len(article) :].strip()
    return part


def _strip_qty(part: str) -> str:
    stripped = _QTY.sub("", part, count=1).strip()
    return stripped or part

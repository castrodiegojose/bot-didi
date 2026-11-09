from datetime import datetime, timedelta, timezone

from didi.food import label
from didi.parser import parse
from didi.suggest import RECIPES, suggest_recipes

RECIPE_LIMIT = 10
BOUGHT_WINDOW = timedelta(hours=48)


def _esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _join_names(items):
    names = [_esc(item["name"]) for item in items]
    if len(names) <= 4:
        return ", ".join(names)
    return f"{', '.join(names[:4])} y más"


def _recent_bought(items):
    cutoff = datetime.now(timezone.utc) - BOUGHT_WINDOW
    bought = []
    for item in items:
        if item["status"] != "bought" or not item.get("boughtAt"):
            continue
        stamp = datetime.fromisoformat(item["boughtAt"].replace("Z", "+00:00"))
        if stamp >= cutoff:
            bought.append(item)
    bought.sort(key=lambda item: item["boughtAt"], reverse=True)
    return bought


def _help(store):
    members = store.members()
    if members:
        who = "En la lista: " + " y ".join(_esc(member["name"]) for member in members) + "."
    else:
        who = "Todavía no hay nadie en la lista."
    return "\n".join(
        [
            "<b>Soy Didi.</b> Anoto el super de los dos y, cuando compran comida, les paso 10 recetas.",
            "",
            "<b>Agregar:</b> agrega leche y huevos, o comprar pan",
            "<b>Sacar uno:</b> eliminar leche, o borra el 2",
            "<b>Borrar la lista antes de comprar:</b> eliminar la lista",
            "<b>Comprado:</b> ya compré pollo",
            "<b>Todo comprado:</b> ya compramos todo",
            "<b>Ir sacando:</b> lista, y tocá el producto para borrarlo",
            "<b>Limpiar comprados:</b> limpiar",
            "<b>Salir:</b> salir",
            "",
            who,
        ]
    )


def _pending(store):
    pending = [item for item in store.items() if item["status"] == "pending"]
    pending.sort(key=lambda item: item["addedAt"])
    return pending


def _checks(store):
    buttons = []
    for item in _pending(store):
        name = item["name"] if len(item["name"]) <= 28 else item["name"][:27] + "…"
        buttons.append({"text": name, "data": f"c:{item['id']}"})
    return buttons


def _list(store):
    pending = _pending(store)
    members = " y ".join(_esc(member["name"]) for member in store.members())
    lines = ["<b>Lista del super</b>", members, ""]
    if not pending:
        if store.shop_done():
            lines.append("Ya compraron todo.")
        else:
            lines.append("La lista está vacía.")
        return "\n".join(lines)
    lines.append(f"Faltan {len(pending)}")
    lines.append("")
    for item in pending:
        lines.append(f"☐ {_esc(item['name'])}")
    lines.extend(["", "Tocá un producto para sacarlo de la lista."])
    return "\n".join(lines)


def _checklist(store, lead="", followup=None, toast=None):
    return _reply(lead + _list(store), checks=_checks(store), followup=followup, toast=toast)


def _recipe_text(recipe):
    ingredients = ", ".join(label(key) for key in recipe["ingredients"])
    steps = "\n".join(f"{index}. {_esc(step)}" for index, step in enumerate(recipe["steps"], start=1))
    return (
        f"<b>{_esc(recipe['name'])}</b>\n{recipe['minutes']} min\n\n"
        f"<b>Ingredientes:</b> {_esc(ingredients)}\n\n{steps}"
    )


def _suggestions(bought):
    foods = [item for item in bought if item["edible"]]
    others = [item for item in bought if not item["edible"]]
    lines = ["<b>Listo, marqué:</b>"]
    lines.extend(f"• {_esc(item['name'])}" for item in foods)
    lines.extend(f"• {_esc(item['name'])} (no se come)" for item in others)
    if not foods:
        lines.extend(["", "No se come, así que no hay recetas."])
        return {"html": "\n".join(lines), "suggestions": []}

    suggestions = suggest_recipes(foods, RECIPE_LIMIT)
    if not suggestions:
        lines.extend(["", "Es comida, pero todavía no tengo recetas cargadas para eso."])
        return {"html": "\n".join(lines), "suggestions": []}

    if len(suggestions) == RECIPE_LIMIT:
        title = f"<b>{RECIPE_LIMIT} recetas con {_join_names(foods)}:</b>"
    else:
        title = (
            f"<b>Tengo {len(suggestions)} recetas con {_join_names(foods)} "
            "(todavía no llego a 10):</b>"
        )
    lines.extend(["", title])
    for index, recipe in enumerate(suggestions, start=1):
        lines.append(f"{index}. {_esc(recipe['name'])} · {recipe['minutes']} min")
    lines.extend(["", "Tocá un número para ver los pasos."])
    return {"html": "\n".join(lines), "suggestions": suggestions}


def _reply(html, suggestions=None, checks=None, followup=None, toast=None):
    return {
        "html": html,
        "suggestions": suggestions or [],
        "checks": checks or [],
        "followup": followup,
        "toast": toast,
        "silent": False,
    }


def handle_message(store, user, text, chat_type=None):
    auth = store.authorize(user)
    if not auth["ok"]:
        return _reply(
            "Esta lista es solo para dos. Si tenés que entrar, la otra persona tiene que escribir <b>salir</b>."
        )

    lead = "Quedaste en la lista compartida.\n\n" if auth["joined"] else ""
    parsed = parse(text)
    kind = parsed["type"]

    if kind == "unknown":
        if chat_type and chat_type != "private":
            return {"silent": True, "html": "", "suggestions": []}
        return _reply(f"{lead}No te entendí. Escribí <b>ayuda</b> y te muestro cómo cargar el super.")

    if kind == "help":
        return _reply(lead + _help(store))
    if kind == "list":
        return _checklist(store, lead)
    if kind == "leave":
        store.leave(user["id"])
        return _reply("Listo, saliste. El lugar queda libre para que entre la otra persona.")
    if kind == "clear_bought":
        removed = store.clear_bought()
        return _reply(f"Borré {removed} comprados." if removed else "No había nada comprado.")
    if kind == "clear_pending":
        removed = store.clear_pending()
        if not removed:
            return _reply("La lista ya estaba vacía.")
        return _reply("Borré la lista.")

    if kind == "add":
        if not parsed.get("items"):
            return _reply("¿Qué agrego? Por ejemplo: agrega leche y pan.")
        result = store.add_items(parsed["items"], user)
        lines = []
        if result["added"]:
            lines.append(f"Anoté: {_join_names(result['added'])}.")
        if result["duplicates"]:
            lines.append("Ya estaba: " + ", ".join(_esc(name) for name in result["duplicates"]) + ".")
        if not lines:
            return _reply("No entendí qué producto.")
        return _checklist(store, lead + "\n".join(lines) + "\n\n")

    if kind == "remove":
        if not parsed.get("items"):
            return _reply("¿Qué saco de la lista?")
        result = store.remove_items(parsed["items"])
        lines = []
        if result["removed"]:
            lines.append(f"Saqué: {_join_names(result['removed'])}.")
        if result["missing"]:
            lines.append("No encontré: " + ", ".join(_esc(name) for name in result["missing"]) + ".")
        if not lines:
            return _reply("No entendí qué producto.")
        return _checklist(store, "\n".join(lines) + "\n\n")

    if kind in {"buy", "buy_all", "buy_smart"}:
        bought = []
        if kind == "buy":
            if not parsed.get("items"):
                return _reply("¿Qué compraron? Por ejemplo: ya compré pollo.")
            bought = store.buy_items(parsed["items"], user)["bought"]
        elif kind == "buy_all":
            bought = store.buy_all(user)["bought"]
            if not bought:
                return _reply("La lista ya está vacía.")
        else:
            pending = [item for item in store.items() if item["status"] == "pending"]
            if not pending:
                return _reply("No hay nada pendiente.")
            if len(pending) > 1:
                return _reply(
                    "Hay varias cosas en la lista. Digan <b>ya compramos todo</b>, o nombren qué compraron."
                )
            bought = store.buy_items([pending[0]["name"]], user)["bought"]
        if not bought:
            return _reply("No entendí qué compraron.")
        result = _suggestions(bought)
        store.set_session(user["id"], [recipe["slug"] for recipe in result["suggestions"]])
        followup = _reply(lead + result["html"], result["suggestions"])
        return _checklist(store, followup=followup)

    if kind == "pick":
        number = parsed["n"]
        if number < 1 or number > RECIPE_LIMIT:
            return _reply("Elegí un número del 1 al 10.")
        slugs = store.session(user["id"])
        slug = slugs[number - 1] if number - 1 < len(slugs) else None
        recipe = next((entry for entry in RECIPES if entry["slug"] == slug), None)
        if not recipe:
            return _reply("No hay recetas abiertas. Cuando marquen algo comprado, les mando ideas.")
        return _reply(_recipe_text(recipe))

    return _reply("No te entendí. Escribí <b>ayuda</b>.")


def mark_checked(store, user, item_id):
    auth = store.authorize(user)
    if not auth["ok"]:
        return _reply(
            "Esta lista es solo para dos. Si tenés que entrar, la otra persona tiene que escribir <b>salir</b>."
        )
    item = store.take_id(item_id)
    if not item:
        return _checklist(store, toast="Ese producto ya no está")
    followup = None
    if not _pending(store):
        foods = [entry for entry in store.take_picked() if entry["edible"]]
        if foods:
            suggested = _suggestions(foods)
            store.set_session(user["id"], [recipe["slug"] for recipe in suggested["suggestions"]])
            followup = _reply(suggested["html"], suggested["suggestions"])
    return _checklist(store, followup=followup, toast=f"Saqué {item['name']}")

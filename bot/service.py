from __future__ import annotations

from bot.db import Database, Item
from bot.edible import is_edible, is_staple, wants_recipes
from bot.parser import parse
from bot.recipes import RecipeClient, RecipeError, format_recipes
from bot.textutil import normalize

HELP = """Lista compartida del super.

Pueden escribir:
• leche, pan y huevos
• agregar detergente
• lista
• ya compré pollo
• ya compramos todo
• borrar pan

Si lo que compraron se come, mando 10 recetas."""

ENTER = "Este bot es solo para los dos. Envíen el código de la casa para entrar."


class GroceryService:
    def __init__(self, db: Database, recipes: RecipeClient, household_code: str):
        self.db = db
        self.recipes = recipes
        self.household_code = normalize(household_code)

    async def reply(self, telegram_id: int, name: str, text: str) -> str:
        if normalize(text) == self.household_code:
            self.db.authorize(telegram_id, name)
            return f"Listo, {name}. Ya estás en la lista de la casa.\n\n{HELP}"
        if not self.db.is_member(telegram_id):
            return ENTER

        intent = parse(text)
        if intent.kind == "help":
            return HELP
        if intent.kind == "list":
            return _format_list(self.db.pending())
        if intent.kind == "add":
            return self._add(list(intent.items), name)
        if intent.kind == "delete":
            return self._delete(list(intent.items))
        if intent.kind == "buy":
            return await self._buy(list(intent.items), name)
        return HELP

    def _add(self, items: list[str], name: str) -> str:
        products = [item for item in items if item != "*"]
        if not products:
            return "Decime qué agrego. Por ejemplo: agregar leche y pan"
        added, existing = self.db.add(products, name)
        lines: list[str] = []
        if added:
            lines.append("Sumé: " + ", ".join(item.display_name for item in added) + ".")
        if existing:
            lines.append("Ya estaba: " + ", ".join(item.display_name for item in existing) + ".")
        return "\n".join(lines)

    def _delete(self, items: list[str]) -> str:
        products = [item for item in items if item != "*"]
        if not products:
            return "Decime qué saco. Por ejemplo: borrar pan"
        deleted, missing = self.db.delete(products)
        lines: list[str] = []
        if deleted:
            lines.append("Saqué: " + ", ".join(item.display_name for item in deleted) + ".")
        if missing:
            lines.append("No estaba: " + ", ".join(missing) + ".")
        return "\n".join(lines)

    async def _buy(self, items: list[str], name: str) -> str:
        if items == ["*"]:
            bought = self.db.buy_all(name)
            if not bought:
                return "La lista ya estaba vacía."
            return await self._recipes_for(bought, bought_line="Compramos todo lo que faltaba.")

        marked, created = self.db.buy(items, name)
        lines: list[str] = []
        if marked:
            lines.append("Comprado: " + ", ".join(item.display_name for item in marked) + ".")
        if created:
            lines.append(
                "No estaba en la lista, lo anoté igual: "
                + ", ".join(item.display_name for item in created)
                + "."
            )
        bought_line = "\n".join(lines)
        return await self._recipes_for([*marked, *created], bought_line=bought_line)

    async def _recipes_for(self, items: list[Item], bought_line: str) -> str:
        cookable = [item for item in items if wants_recipes(item.display_name)]
        household = [item for item in items if not is_edible(item.display_name)]
        staples = [item for item in items if is_staple(item.display_name)]
        lines = [bought_line]
        if household:
            names = ", ".join(item.display_name for item in household)
            lines.append(f"Sin recetas, porque no se come: {names}.")
        if not cookable:
            if staples:
                names = ", ".join(item.display_name for item in staples)
                lines.append(f"{names} es de despensa. No armé recetas solo con eso.")
            return "\n\n".join(lines)

        labels = [item.display_name for item in cookable[:5]]
        try:
            recipes = await self.recipes.recommend(labels)
        except RecipeError:
            lines.append("No pude buscar recetas ahora. Igual quedó anotado como comprado.")
            return "\n\n".join(lines)
        if len(cookable) > 5:
            lines.append("Busqué recetas con " + ", ".join(labels) + ".")
        lines.append(format_recipes(labels, recipes))
        return "\n\n".join(line for line in lines if line)


def _format_list(items: list[Item]) -> str:
    if not items:
        return "La lista está vacía. Escriban por ejemplo: leche, pan y huevos"
    lines = [f"Hay que comprar ({len(items)}):"]
    for item in items:
        who = f" · {item.added_by}" if item.added_by else ""
        lines.append(f"• {item.display_name}{who}")
    lines.append("")
    lines.append("Cuando vuelvan: ya compré pollo")
    return "\n".join(lines)

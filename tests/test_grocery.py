from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from bot.db import Database
from bot.edible import is_edible, is_staple, wants_recipes
from bot.ingredients import ingredient_queries
from bot.parser import parse
from bot.recipes import Recipe, RecipeError, mix
from bot.service import GroceryService


class ParseTests(unittest.TestCase):
    def test_bare_items_are_added(self) -> None:
        intent = parse("leche, pan y huevos")
        self.assertEqual(intent.kind, "add")
        self.assertEqual(intent.items, ("leche", "pan", "huevos"))

    def test_accented_buy_keeps_the_product(self) -> None:
        intent = parse("Ya compré pollo")
        self.assertEqual(intent.kind, "buy")
        self.assertEqual(intent.items, ("pollo",))

    def test_buy_everything(self) -> None:
        self.assertEqual(parse("ya compramos").items, ("*",))
        self.assertEqual(parse("ya compré todo").items, ("*",))

    def test_list_delete_and_quantity(self) -> None:
        self.assertEqual(parse("lista").kind, "list")
        self.assertEqual(parse("/lista@superbot").kind, "list")
        self.assertEqual(parse("borrar la leche").items, ("leche",))
        self.assertEqual(parse("2 kg de papas").items, ("papas",))
        self.assertEqual(parse("una docena de huevos").items, ("huevos",))

    def test_greeting_is_help(self) -> None:
        self.assertEqual(parse("hola").kind, "help")


class FoodTests(unittest.TestCase):
    def test_edible_household_and_staples(self) -> None:
        self.assertTrue(wants_recipes("pollo"))
        self.assertFalse(is_edible("detergente"))
        self.assertFalse(is_edible("papel higiénico"))
        self.assertTrue(is_edible("papel de arroz"))
        self.assertTrue(is_staple("sal"))
        self.assertFalse(wants_recipes("aceite de oliva"))
        self.assertFalse(is_staple("salchicha"))

    def test_ingredient_names(self) -> None:
        self.assertEqual(ingredient_queries("papas"), ["Potatoes"])
        self.assertEqual(ingredient_queries("pechuga de pollo"), ["Chicken Breast"])
        self.assertEqual(ingredient_queries("arroz con pollo"), ["Rice", "Chicken"])


class RecipeMixTests(unittest.TestCase):
    def test_mix_is_unique_and_capped(self) -> None:
        chicken = [_recipe(str(i), f"c{i}") for i in range(4)]
        rice = [_recipe(str(i + 10), f"r{i}") for i in range(4)]
        rice[0] = chicken[0]
        picked = mix([chicken, rice], limit=10, seed="fijo")
        self.assertLessEqual(len(picked), 10)
        self.assertEqual(len(picked), len({item.meal_id for item in picked}))


class ServiceTests(unittest.TestCase):
    def test_shared_list_and_recipes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "lista.db")
            recipes = FakeRecipes()
            service = GroceryService(db, recipes, "secreto")
            blocked = asyncio.run(service.reply(1, "Diego", "leche"))
            self.assertIn("código", blocked)
            self.assertEqual(db.pending(), [])

            asyncio.run(service.reply(1, "Diego", "secreto"))
            asyncio.run(service.reply(2, "Ana", "secreto"))
            asyncio.run(service.reply(1, "Diego", "leche, pan y detergente"))
            listed = asyncio.run(service.reply(2, "Ana", "lista"))
            self.assertIn("leche", listed)
            self.assertIn("Diego", listed)

            bought = asyncio.run(service.reply(2, "Ana", "ya compré pollo y detergente"))
            self.assertIn("Brown Stew Chicken", bought)
            self.assertIn("https://www.themealdb.com/meal/1", bought)
            self.assertIn("no se come", bought)
            self.assertEqual(recipes.calls, [["pollo"]])
            self.assertEqual(db.pending()[0].display_name, "leche")
            db.close()

    def test_detergent_skips_recipes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "lista.db")
            recipes = FakeRecipes()
            service = GroceryService(db, recipes, "secreto")
            asyncio.run(service.reply(1, "Diego", "secreto"))
            reply = asyncio.run(service.reply(1, "Diego", "ya compré detergente"))
            self.assertIn("no se come", reply)
            self.assertEqual(recipes.calls, [])
            db.close()

    def test_recipe_outage_still_marks_bought(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "lista.db")
            service = GroceryService(db, FakeRecipes(fail=True), "secreto")
            asyncio.run(service.reply(1, "Diego", "secreto"))
            asyncio.run(service.reply(1, "Diego", "agregar pollo"))
            reply = asyncio.run(service.reply(1, "Diego", "ya compré pollo"))
            self.assertIn("No pude buscar recetas", reply)
            self.assertEqual(db.pending(), [])
            db.close()


class FakeRecipes:
    def __init__(self, recipes: list[Recipe] | None = None, fail: bool = False):
        self.recipes = recipes or [Recipe("1", "Brown Stew Chicken", "https://www.themealdb.com/meal/1")]
        self.fail = fail
        self.calls: list[list[str]] = []

    async def recommend(self, names: list[str], limit: int = 10) -> list[Recipe]:
        self.calls.append(list(names))
        if self.fail:
            raise RecipeError("down")
        return self.recipes[:limit]


def _recipe(meal_id: str, name: str) -> Recipe:
    return Recipe(meal_id, name, f"https://www.themealdb.com/meal/{meal_id}")


if __name__ == "__main__":
    unittest.main()

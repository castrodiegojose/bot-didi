import tempfile
import unittest
from pathlib import Path

from didi.food import clean_name, is_edible, keywords
from didi.handle import handle_message, mark_checked
from didi.parser import parse
from didi.store import Store
from didi.suggest import RECIPES, suggest_recipes

STAPLES = [
    "pollo",
    "carne",
    "cerdo",
    "pescado",
    "atun",
    "huevo",
    "arroz",
    "fideo",
    "papa",
    "tomate",
    "queso",
    "leche",
    "cebolla",
    "lenteja",
    "yogur",
]


class BotTest(unittest.TestCase):
    def test_normaliza_cantidades_y_acentos(self):
        self.assertEqual(clean_name("2 kg de papas"), "papas")
        self.assertEqual(clean_name("1 litro de leche"), "leche")
        self.assertEqual(keywords("pechuga de pollo"), ["pollo"])
        self.assertEqual(keywords("Limón"), ["limon"])
        self.assertEqual(sorted(keywords("crema de leche")), ["crema", "leche"])
        self.assertFalse(is_edible("lavandina"))
        self.assertTrue(is_edible("bolsa de leche"))
        self.assertFalse(is_edible("papel higiénico"))
        self.assertTrue(is_edible("2 kg de papas"))

    def test_entiende_como_hablan(self):
        self.assertEqual(
            parse("Agregá leche, huevos y pan"),
            {"type": "add", "items": ["leche", "huevos", "pan"]},
        )
        bought = parse("Ya compré limón")
        self.assertEqual(bought["type"], "buy")
        self.assertEqual(bought["items"], ["limón"])
        self.assertEqual(parse("ya compramos todo")["type"], "buy_all")
        self.assertEqual(parse("lista")["type"], "list")
        self.assertEqual(parse("/agregar café y azúcar")["type"], "add")
        self.assertEqual(
            parse("comprar leche y pan"),
            {"type": "add", "items": ["leche", "pan"]},
        )
        self.assertEqual(parse("compra manteca")["type"], "add")
        self.assertEqual(parse("eliminar leche")["type"], "remove")
        self.assertEqual(parse("borra el 2")["items"], ["2"])
        self.assertEqual(parse("eliminar la lista")["type"], "clear_pending")
        self.assertEqual(parse("3"), {"type": "pick", "n": 3})
        self.assertEqual(parse("hola")["type"], "help")

    def test_cada_alimento_tiene_diez_recetas(self):
        for staple in STAPLES:
            got = suggest_recipes([{"edible": True, "keywords": [staple]}])
            self.assertEqual(len(got), 10, staple)
            self.assertTrue(all(staple in recipe["ingredients"] for recipe in got), staple)

    def test_lista_compartida_y_recetas(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "household.json")
            diego = {"id": 1, "name": "Diego"}
            agus = {"id": 2, "name": "Agus"}
            otro = {"id": 3, "name": "Otro"}

            added = handle_message(store, diego, "agrega leche, pechuga de pollo y lavandina")
            self.assertRegex(added["html"], r"Anoté")
            self.assertRegex(added["html"], r"Quedaste en la lista")

            again = handle_message(store, agus, "necesito leche")
            self.assertRegex(again["html"], r"Ya estaba")

            bought = handle_message(store, diego, "ya compré pollo y lavandina")
            self.assertRegex(bought["html"], r"☐ Leche")
            self.assertNotRegex(bought["html"], r"Pechuga de pollo")
            self.assertNotRegex(bought["html"], r"Lavandina")
            self.assertRegex(bought["followup"]["html"], r"10 recetas")
            self.assertRegex(bought["followup"]["html"], r"no se come")
            self.assertEqual(len(bought["followup"]["suggestions"]), 10)
            self.assertTrue(
                all("pollo" in recipe["ingredients"] for recipe in bought["followup"]["suggestions"])
            )

            recipe = handle_message(store, diego, "2")
            self.assertRegex(recipe["html"], r"Ingredientes")
            self.assertEqual(recipe["suggestions"], [])

            listing = handle_message(store, agus, "qué falta")
            self.assertRegex(listing["html"], r"Faltan 1")
            self.assertRegex(listing["html"], r"☐ Leche")
            self.assertNotRegex(listing["html"], r"Pechuga de pollo")
            self.assertEqual(len(listing["checks"]), 1)
            self.assertIn("Leche", listing["checks"][0]["text"])

            rejected = handle_message(store, otro, "agrega pan")
            self.assertRegex(rejected["html"], r"solo para dos")

            reopened = Store(store.path)
            pending = [item for item in reopened.items() if item["status"] == "pending"]
            self.assertEqual(len(pending), 1)
            self.assertGreater(len(RECIPES), 100)

    def test_elimina_un_producto_o_la_lista_antes_de_comprar(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "household.json")
            diego = {"id": 1, "name": "Diego"}
            handle_message(store, diego, "agrega leche, pan y huevos")

            one = handle_message(store, diego, "eliminar leche")
            self.assertRegex(one["html"], r"Leche")
            pending = [item["name"] for item in store.items() if item["status"] == "pending"]
            self.assertEqual(pending, ["Pan", "Huevos"])

            second = handle_message(store, diego, "borra el 1")
            self.assertRegex(second["html"], r"Pan")
            pending = [item["name"] for item in store.items() if item["status"] == "pending"]
            self.assertEqual(pending, ["Huevos"])

            bought = handle_message(store, diego, "ya compré huevos")
            self.assertNotRegex(bought["html"], r"Huevos")
            self.assertEqual(
                [item["name"] for item in store.items() if item["status"] == "pending"],
                [],
            )
            handle_message(store, diego, "comprar café")
            cleared = handle_message(store, diego, "eliminar la lista")
            self.assertRegex(cleared["html"], r"Borré la lista")
            self.assertEqual(store.items(), [])

    def test_tachar_un_producto_actualiza_el_checklist(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "household.json")
            diego = {"id": 1, "name": "Diego"}
            handle_message(store, diego, "agrega leche y pollo")
            pending = [item for item in store.items() if item["status"] == "pending"]
            first = mark_checked(store, diego, pending[0]["id"])
            self.assertRegex(first["html"], r"Faltan 1")
            self.assertNotRegex(first["html"], r"Leche")
            self.assertRegex(first["html"], r"☐ Pollo")
            self.assertEqual(first["toast"], "Saqué Leche")
            self.assertIsNone(first["followup"])
            self.assertEqual(len(first["checks"]), 1)
            self.assertIn("Pollo", first["checks"][0]["text"])

            last = mark_checked(store, diego, pending[1]["id"])
            self.assertRegex(last["html"], r"Ya compraron todo")
            self.assertNotRegex(last["html"], r"Pollo")
            self.assertEqual(last["checks"], [])
            self.assertRegex(last["followup"]["html"], r"10 recetas")

            again = handle_message(store, diego, "lista")
            self.assertRegex(again["html"], r"Ya compraron todo")

            fresh = handle_message(store, diego, "agrega café")
            self.assertRegex(fresh["html"], r"☐ Café")
            self.assertNotRegex(fresh["html"], r"Ya compraron todo")


if __name__ == "__main__":
    unittest.main()

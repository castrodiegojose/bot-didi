from __future__ import annotations

from bot.textutil import contains_phrase, normalize

# Nombres que TheMealDB acepta en filter.php?i=
PHRASES: dict[str, str] = {
    "carne molida": "Minced Beef",
    "pechuga de pollo": "Chicken Breast",
    "queso crema": "Cream Cheese",
    "crema de leche": "Cream",
    "dulce de leche": "Dulce de leche",
    "leche condensada": "Condensed Milk",
    "mantequilla de mani": "Peanut Butter",
    "porotos negros": "Black Beans",
    "frijoles negros": "Black Beans",
    "salsa de tomate": "Tomato Sauce",
    "papel de arroz": "Rice Paper Sheets",
}
WORDS: dict[str, str] = {
    "pollo": "Chicken",
    "pechuga": "Chicken Breast",
    "carne": "Beef",
    "vacuno": "Beef",
    "res": "Beef",
    "cerdo": "Pork",
    "chancho": "Pork",
    "puerco": "Pork",
    "cordero": "Lamb",
    "pavo": "Turkey",
    "jamon": "Ham",
    "tocino": "Bacon",
    "panceta": "Bacon",
    "chorizo": "Chorizo",
    "salchicha": "Sausages",
    "salchichas": "Sausages",
    "atun": "Tuna",
    "salmon": "Salmon",
    "camaron": "Prawns",
    "camarones": "Prawns",
    "langostino": "Prawns",
    "langostinos": "Prawns",
    "gamba": "Prawns",
    "gambas": "Prawns",
    "pescado": "White Fish",
    "merluza": "White Fish",
    "tofu": "Tofu",
    "leche": "Milk",
    "queso": "Cheese",
    "crema": "Cream",
    "mantequilla": "Butter",
    "manteca": "Butter",
    "yogur": "Yogurt",
    "yogurt": "Yogurt",
    "yoghurt": "Yogurt",
    "huevo": "Egg",
    "huevos": "Eggs",
    "mozzarella": "Mozzarella",
    "parmesano": "Parmesan",
    "cheddar": "Cheddar Cheese",
    "feta": "Feta",
    "tomate": "Tomato",
    "tomates": "Tomatoes",
    "cebolla": "Onion",
    "cebollas": "Onions",
    "ajo": "Garlic",
    "papa": "Potatoes",
    "papas": "Potatoes",
    "patata": "Potatoes",
    "patatas": "Potatoes",
    "batata": "Sweet Potatoes",
    "camote": "Sweet Potatoes",
    "boniato": "Sweet Potatoes",
    "zanahoria": "Carrots",
    "zanahorias": "Carrots",
    "lechuga": "Lettuce",
    "espinaca": "Spinach",
    "brocoli": "Broccoli",
    "zapallo": "Pumpkin",
    "calabaza": "Pumpkin",
    "zapallito": "Zucchini",
    "zucchini": "Zucchini",
    "pepino": "Cucumber",
    "pimenton": "Red Pepper",
    "pimiento": "Red Pepper",
    "morron": "Red Pepper",
    "aji": "Chilli",
    "palta": "Avocado",
    "aguacate": "Avocado",
    "limon": "Lemon",
    "lima": "Lime",
    "naranja": "Orange",
    "manzana": "Apples",
    "manzanas": "Apples",
    "pera": "Pears",
    "peras": "Pears",
    "durazno": "Peaches",
    "melocoton": "Peaches",
    "banana": "Banana",
    "bananas": "Banana",
    "platano": "Banana",
    "cambur": "Banana",
    "frutilla": "Strawberries",
    "frutillas": "Strawberries",
    "fresa": "Strawberries",
    "fresas": "Strawberries",
    "mango": "Mango",
    "coco": "Coconut",
    "champinon": "Mushrooms",
    "champinones": "Mushrooms",
    "hongo": "Mushrooms",
    "hongos": "Mushrooms",
    "arveja": "Peas",
    "arvejas": "Peas",
    "guisante": "Peas",
    "guisantes": "Peas",
    "choclo": "Sweetcorn",
    "elote": "Sweetcorn",
    "maiz": "Sweetcorn",
    "poroto": "Kidney Beans",
    "porotos": "Kidney Beans",
    "frijol": "Kidney Beans",
    "frijoles": "Kidney Beans",
    "lenteja": "Lentils",
    "lentejas": "Lentils",
    "garbanzo": "Chickpeas",
    "garbanzos": "Chickpeas",
    "repollo": "Cabbage",
    "col": "Cabbage",
    "berenjena": "Aubergine",
    "apio": "Celery",
    "puerro": "Leek",
    "remolacha": "Beetroot",
    "betarraga": "Beetroot",
    "rucula": "Rocket",
    "kale": "Kale",
    "esparrago": "Asparagus",
    "esparragos": "Asparagus",
    "arroz": "Rice",
    "fideo": "Spaghetti",
    "fideos": "Spaghetti",
    "pasta": "Spaghetti",
    "tallarin": "Spaghetti",
    "tallarines": "Spaghetti",
    "espagueti": "Spaghetti",
    "macarrones": "Macaroni",
    "pan": "Bread",
    "avena": "Oats",
    "quinoa": "Quinoa",
    "miel": "Honey",
    "chocolate": "Dark Chocolate",
    "cacao": "Cocoa",
    "mani": "Peanuts",
    "nuez": "Walnuts",
    "nueces": "Walnuts",
    "almendra": "Almonds",
    "almendras": "Almonds",
    "aceituna": "Green Olives",
    "aceitunas": "Green Olives",
    "vino": "Red Wine",
    "cerveza": "Beer",
    "mayonesa": "Mayonnaise",
    "ketchup": "Tomato Sauce",
    "mostaza": "Mustard",
    "tortilla": "Tortillas",
    "tortillas": "Tortillas",
    "jengibre": "Ginger",
    "cilantro": "Cilantro",
    "perejil": "Parsley",
    "albahaca": "Basil",
}
STOPWORDS = {"de", "con", "y", "e", "para", "al", "del", "la", "el", "los", "las", "un", "una"}


def ingredient_queries(name: str) -> list[str]:
    normalized = normalize(name)
    found: list[str] = []
    for phrase, query in sorted(PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        if contains_phrase(normalized, phrase):
            _add(found, query)
    if found:
        return found[:3]
    for token in _tokens(normalized):
        query = WORDS.get(token)
        if query:
            _add(found, query)
    return found[:3]


def _tokens(name: str) -> list[str]:
    tokens: list[str] = []
    for token in name.split():
        if token in STOPWORDS:
            continue
        tokens.append(token)
        if token.endswith("es") and len(token) > 4:
            tokens.append(token[:-2])
        elif token.endswith("s") and len(token) > 3:
            tokens.append(token[:-1])
    return tokens


def _add(found: list[str], query: str) -> None:
    if query not in found:
        found.append(query)

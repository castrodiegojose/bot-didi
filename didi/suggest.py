import json
from pathlib import Path

RECIPES = json.loads((Path(__file__).with_name("recipes.json")).read_text(encoding="utf-8"))


def suggest_recipes(items, limit=10, book=None):
    catalog = RECIPES if book is None else book
    keys = set()
    for item in items:
        if item.get("edible"):
            keys.update(item.get("keywords") or [])
    if not keys:
        return []

    ranked = []
    for recipe in catalog:
        score = sum(1 for key in recipe["ingredients"] if key in keys)
        if score <= 0:
            continue
        main = 1 if recipe["ingredients"][0] in keys else 0
        ranked.append((score, main, recipe))
    ranked.sort(key=lambda entry: (-entry[0], -entry[1], entry[2]["name"]))
    return [entry[2] for entry in ranked[:limit]]

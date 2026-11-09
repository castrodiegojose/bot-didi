from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date

import httpx

from bot.ingredients import ingredient_queries

MEALDB_FILTER = "https://www.themealdb.com/api/json/v1/1/filter.php"


class RecipeError(Exception):
    pass


@dataclass(frozen=True)
class Recipe:
    meal_id: str
    name: str
    url: str


class RecipeClient:
    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self._cache: dict[str, list[Recipe]] = {}

    async def recommend(self, names: list[str], limit: int = 10) -> list[Recipe]:
        groups: list[list[Recipe]] = []
        for name in names[:5]:
            group = await self._for_name(name)
            if group:
                groups.append(group)
        seed = f"{date.today().isoformat()}:{'|'.join(names[:5])}"
        return mix(groups, limit, seed)

    async def _for_name(self, name: str) -> list[Recipe]:
        for query in ingredient_queries(name):
            recipes = await self._search(query)
            if recipes:
                return recipes
        return []

    async def _search(self, query: str) -> list[Recipe]:
        cached = self._cache.get(query)
        if cached is not None:
            return cached
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": "bot-didi/1.0"},
            ) as client:
                response = await client.get(MEALDB_FILTER, params={"i": query})
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RecipeError("No pude consultar recetas") from exc
        recipes = _parse_meals(payload)
        self._cache[query] = recipes
        return recipes


def mix(groups: list[list[Recipe]], limit: int, seed: str) -> list[Recipe]:
    rng = random.Random(seed)
    shuffled: list[list[Recipe]] = []
    for group in groups:
        copy = list(group)
        rng.shuffle(copy)
        shuffled.append(copy)
    picked: list[Recipe] = []
    seen: set[str] = set()
    longest = max((len(group) for group in shuffled), default=0)
    for index in range(longest):
        for group in shuffled:
            if index >= len(group):
                continue
            recipe = group[index]
            if recipe.meal_id in seen:
                continue
            picked.append(recipe)
            seen.add(recipe.meal_id)
            if len(picked) == limit:
                return picked
    return picked


def format_recipes(labels: list[str], recipes: list[Recipe]) -> str:
    names = ", ".join(labels)
    if not recipes:
        return f"No encontré recetas para {names}."
    lines = [f"{len(recipes)} recetas con {names}:"]
    blocks = [f"{number}. {recipe.name}\n{recipe.url}" for number, recipe in enumerate(recipes, start=1)]
    lines.append("\n\n".join(blocks))
    lines.append("En inglés, de TheMealDB.")
    return "\n\n".join(lines)


def _parse_meals(payload: object) -> list[Recipe]:
    if not isinstance(payload, dict):
        return []
    meals = payload.get("meals") or []
    if not isinstance(meals, list):
        return []
    recipes: list[Recipe] = []
    for meal in meals:
        if not isinstance(meal, dict):
            continue
        meal_id = str(meal.get("idMeal") or "").strip()
        name = str(meal.get("strMeal") or "").strip()
        if meal_id and name:
            recipes.append(Recipe(meal_id, name, f"https://www.themealdb.com/meal/{meal_id}"))
    return recipes

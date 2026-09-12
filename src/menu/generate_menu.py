#!/usr/bin/env python3

from dataclasses import dataclass
from glob import glob
import json
from random import shuffle
import re
import subprocess
from typing import Any


@dataclass
class Metadata:
    tags: list[str]
    source: str
    filename: str


@dataclass
class Recipe:
    name: str
    ingredients: list[str]
    metadata: Metadata


@dataclass
class Recipes:
    recipes: list[Recipe]

    def by_tag(self, tag: str) -> list[Recipe]:
        return [r for r in self.recipes if tag in r.metadata.tags]


def generate_menu(recipes: Recipes, days=7) -> list[dict[str, Recipe]]:
    categories = ["主食", "肉菜", "素菜"]
    recipes_by_category = {}
    for category in categories:
        meals = recipes.by_tag(category)
        if len(meals) < days:
            raise ValueError(
                f"Category {category} do not have enough recipes, want {days} got {len(meals)}"
            )
        shuffle(meals)
        recipes_by_category[category] = meals

    result = []
    for d in range(days):
        per_day = {}
        for category in categories:
            per_day[category] = recipes_by_category[category][d]
        result.append(per_day)
    return result


def extract_recipes(pathname: str) -> Recipes:
    result = []
    for filename in glob(pathname):
        res = subprocess.run(
            ["cook", "recipe", "--format", "json", filename],
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(res.stdout)
        metadata = Metadata(
            tags = data["metadata"]["map"]["tags"],
            source = data["metadata"]["map"]["source"],
            filename = filename,
        )
        recipe = Recipe(
            name = data["metadata"]["map"]["title"],
            ingredients = [i["name"] for i in data["ingredients"]],
            metadata = metadata
        )
        result.append(recipe)
    return Recipes(result)


if __name__ == "__main__":
    main()

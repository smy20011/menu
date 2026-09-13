#!/usr/bin/env python3

import argparse
import json
import subprocess
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from random import shuffle
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

@dataclass
class Menu:
    menu: list[dict[str, Recipe]]

    def cooklang_menu(self, starting_date: datetime) -> str:
        fragments = []
        for day, menu_day in enumerate(self.menu):
            date = starting_date + timedelta(day)
            fragments.append(date.strftime('== %A (%Y-%m-%d) =='))
            fragments.append("")
            for category, recipe in self.menu[day].items():
                fragments.append(f"{category}: @./{recipe.metadata.filename}{{}}")
                fragments.append("")
            fragments.append("")
        return "\n".join(fragments)

def cook_cli(*args: str, parse_json=True) -> Any:
    result = subprocess.run(["cook"] + list(args), text=True, check=True, capture_output=True).stdout
    if parse_json:
        return json.loads(result)
    else:
        return result

def generate_menu(recipes: Recipes, days=7) -> Menu:
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
    return Menu(result)


def extract_recipes(pathname: str) -> Recipes:
    result = []
    for filename in glob(pathname):
        data = cook_cli("recipe", "--format", "json", filename)
        metadata = Metadata(
            tags=data["metadata"]["map"]["tags"],
            source=data["metadata"]["map"]["source"],
            filename=filename,
        )
        recipe = Recipe(
            name=data["metadata"]["map"]["title"],
            ingredients=[i["name"] for i in data["ingredients"]],
            metadata=metadata,
        )
        result.append(recipe)
    return Recipes(result)

def write_menu(menu: Menu, date: datetime, dest: Path, override: bool = False):
    if dest.exists() and not override:
        print(f"{dest} already exists, use -f to override.")
        return
    dest.write_text(menu.cooklang_menu(date))

def write_report(menu_file: Path, date: datetime, dest: Path):
    data = cook_cli("shopping-list", "--format", "json", str(menu_file))
    result = ["# 菜谱", "## 购物清单"]
    for category in data:
        result.append(f"### {category['category']}")
        result.append("")
        for item in category["items"]:
            result.append(f"- [ ] {item['name']}")
        result.append("")

    result.append("## 每日菜谱")
    menu_text = cook_cli("recipe", "--format", "markdown", str(menu_file), parse_json=False)
    menu_text = re.sub("# .*Steps", "", menu_text, flags=re.DOTALL)
    menu_text = re.sub("\\.cook", "", menu_text)
    result.append(menu_text)
    dest.write_text("\n".join(result))

def main():
    parser = argparse.ArgumentParser("Menu Gen: Generate Random Menu")
    parser.add_argument("-f", '--force', action='store_true', help='Override existing menus')
    parser.add_argument("--glob", help="Glob pattern for cook files, default *.cook", default="**/*.cook")
    parser.add_argument("--days", help="Number of days to generate", default=7, type=int)
    parser.add_argument('date', help='Generate Menu for following date, should be in format like 2026-01-23')
    opts = parser.parse_args()

    date = datetime.strptime(opts.date, "%Y-%m-%d")

    recipes = extract_recipes(opts.glob)
    menu = generate_menu(recipes, opts.days)
    menu_dest = Path("menus") / date.strftime("%Y-%m-%d.menu")
    report_dest = Path("menus") / date.strftime("%Y-%m-%d.md")
    write_menu(menu, date, menu_dest, override=opts.force)
    write_report(menu_dest, date, report_dest)

if __name__ == "__main__":
    main()

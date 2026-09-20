#!/usr/bin/env python3

import argparse
import json
import subprocess
import re
import tomllib
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

    def by_tag(self, *tags: str) -> list[Recipe]:
        result = []
        for r in self.recipes:
            if all([tag in r.metadata.tags for tag in tags]):
                result.append(r)
        return result

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

def generate_menu(recipes: Recipes, config: Any, date: datetime, days=7) -> Menu:
    recipes_by_category = {}
    categories = list(config.keys())
    for name, category in config.items():
        # Make sure there is no OOB
        tags = category['tags']
        meals = recipes.by_tag(*tags)
        if len(meals) < days:
            meals = meals * days
        shuffle(meals)
        if len(meals) == 0:
            raise ValueError(f"Cannot find recipes for tags {tags}")
        recipes_by_category[name] = meals

    result = []
    for d in range(days):
        current_date = date + timedelta(days = d)
        per_day = {}
        for category in categories:
            days = config[category].get("days", list(range(7)))
            if current_date.weekday() in days:
                per_day[category] = recipes_by_category[category][d]
        result.append(per_day)
    return Menu(result)


def extract_recipes(pathname: str) -> Recipes:
    result = []
    for filename in glob(pathname):
        data = cook_cli("recipe", "--format", "json", filename)
        metadata = Metadata(
            tags=data["metadata"]["map"]["tags"],
            source=data["metadata"]["map"].get("source", ""),
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

def write_report(menu_file: Path, recipes: Recipes, date: datetime, dest: Path):
    data = cook_cli("shopping-list", "--format", "json", str(menu_file))
    result = ["# 菜谱", "## 购物清单"]
    for category in data:
        result.append(f"### {category['category']}")
        result.append("")
        for item in category["items"]:
            result.append(f"- [ ] {item['name']}")
        result.append("")

    data = cook_cli("recipe", "--format", "json", str(menu_file))
    result.append("## 每日菜谱")
    found_recipes: list[Recipe] = []
    for section in data['sections']:
        result.append(f"### {section['name']}")
        for idx, steps in enumerate(section['content']):
            line = f"{idx + 1}. "
            for item in steps["value"]['items']:
                if item['type'] == 'text':
                    line += item['value']
                else:
                    ingredient = data['ingredients'][item['index']]
                    full_path = "/".join(ingredient['reference']['components'] + [ingredient['reference']['name']])
                    found = [r for r in recipes.recipes if full_path.endswith(r.metadata.filename)]
                    assert len(found) > 0, f"Cannot find recipe {full_path}"
                    recipe = found[0]
                    found_recipes.append(recipe)
                    if recipe.metadata.source.startswith("http"):
                        line += f"[{recipe.name}]({recipe.metadata.source})"
                    else:
                        line += f"{recipe.name}"
            result.append(line)
        result.append("")

    result.append("## 做法")
    for recipe in found_recipes:
        if recipe.metadata.source.startswith("http"):
            result.append(f"### {recipe.name}")
            result.append(f"[原视频]({recipe.metadata.source})")
            md = cook_cli("recipe", "--format", "markdown", recipe.metadata.filename, parse_json=False)
            md = re.sub(".*Steps", "", md, flags=re.DOTALL)
            result.append(md)

    dest.write_text("\n".join(result))

def load_config(path: str):
    with open(path, "rb") as f:
        return tomllib.load(f)

def main():
    parser = argparse.ArgumentParser("Menu Gen: Generate Random Menu")
    parser.add_argument("-f", '--force', action='store_true', help='Override existing menus')
    parser.add_argument("--glob", help="Glob pattern for cook files, default *.cook", default="**/*.cook")
    parser.add_argument("--days", help="Number of days to generate", default=7, type=int)
    parser.add_argument("--config", help="Menu generation config", default="config.toml")
    parser.add_argument('date', help='Generate Menu for following date, should be in format like 2026-01-23')
    opts = parser.parse_args()

    date = datetime.strptime(opts.date, "%Y-%m-%d")
    config = load_config(opts.config)

    recipes = extract_recipes(opts.glob)
    menu = generate_menu(recipes, config, date, opts.days)
    menu_dest = Path("menus") / date.strftime("%Y-%m-%d.menu")
    report_dest = Path("menus") / date.strftime("%Y-%m-%d.md")
    write_menu(menu, date, menu_dest, override=opts.force)
    write_report(menu_dest, recipes, date, report_dest)

if __name__ == "__main__":
    main()

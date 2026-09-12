#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cooklang Random Weekly Menu Generator
Dynamically scans .cook files, categorizes dishes by YAML tags (主食/肉菜/素菜/零食),
and generates a balanced weekly menu for the upcoming Monday in the `menus/` folder.
Conforms strictly to Cooklang Menu specification:
https://cooklang.org/docs/conventions/#menu-files
"""

import os
import re
import glob
import random
import argparse
from datetime import datetime, timedelta, date

DAYS_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def get_next_monday(base_date=None):
    """
    Calculate the next Monday relative to base_date (defaults to today).
    If base_date is already a Monday, returns the upcoming Monday (7 days later).
    """
    if base_date is None:
        base_date = date.today()
    elif isinstance(base_date, str):
        base_date = datetime.strptime(base_date, "%Y-%m-%d").date()

    days_ahead = (0 - base_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base_date + timedelta(days=days_ahead)

def parse_cook_metadata(filepath):
    """
    Extract title and tags from a .cook file's YAML frontmatter.
    """
    tags = []
    title = os.path.splitext(os.path.basename(filepath))[0]
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            t_match = re.search(r"^title:\s*(.+)$", fm_text, re.MULTILINE)
            if t_match:
                title = t_match.group(1).strip()
            
            in_tags = False
            for line in fm_text.splitlines():
                line = line.rstrip()
                if re.match(r"^tags:\s*$", line):
                    in_tags = True
                    continue
                if in_tags:
                    tag_match = re.match(r"^\s*-\s*(.+)$", line)
                    if tag_match:
                        tags.append(tag_match.group(1).strip())
                    elif line and not line.startswith(" "):
                        in_tags = False
    except Exception as e:
        print(f"Warning: Failed to parse {filepath}: {e}")

    return {
        "filename": os.path.basename(filepath),
        "name": os.path.splitext(os.path.basename(filepath))[0],
        "title": title,
        "tags": tags
    }

def load_and_categorize_recipes(recipes_dir):
    """
    Scan recipes_dir for .cook files and categorize them into 主食, 肉菜, 素菜, 零食.
    """
    categories = {
        "主食": [],
        "肉菜": [],
        "素菜": [],
        "零食": []
    }

    cook_files = glob.glob(os.path.join(recipes_dir, "*.cook"))
    for f in cook_files:
        meta = parse_cook_metadata(f)
        tags = set(meta["tags"])
        
        categorized = False
        for cat in categories.keys():
            if cat in tags:
                categories[cat].append(meta["name"])
                categorized = True
        
        if not categorized:
            categories["素菜"].append(meta["name"])

    return categories

def build_random_menu(categories, days=7, include_snack_on_weekends=True):
    """
    Randomly select non-repeating dishes for each day.
    """
    staples_pool = list(categories.get("主食", []))
    meats_pool = list(categories.get("肉菜", []))
    veggies_pool = list(categories.get("素菜", []))
    snacks_pool = list(categories.get("零食", []))

    random.shuffle(staples_pool)
    random.shuffle(meats_pool)
    random.shuffle(veggies_pool)
    random.shuffle(snacks_pool)

    menu_plan = []
    for i in range(days):
        day_name = DAYS_ZH[i % len(DAYS_ZH)]
        
        if not staples_pool:
            staples_pool = list(categories.get("主食", []))
            random.shuffle(staples_pool)
        if not meats_pool:
            meats_pool = list(categories.get("肉菜", []))
            random.shuffle(meats_pool)
        if not veggies_pool:
            veggies_pool = list(categories.get("素菜", []))
            random.shuffle(veggies_pool)

        day_dishes = [
            staples_pool.pop(),
            meats_pool.pop(),
            veggies_pool.pop()
        ]

        if include_snack_on_weekends and day_name in ["周六", "周日"] and snacks_pool:
            day_dishes.append(snacks_pool.pop())

        menu_plan.append({
            "day": day_name,
            "dishes": day_dishes
        })

    return menu_plan

def format_cooklang_menu(menu_plan, start_date=None, servings=None):
    """
    Format menu plan conforming to Cooklang Menu Spec.
    """
    servings_str = f"{{{servings}}}" if servings else "{}"
    lines = []

    cur_date = start_date

    for item in menu_plan:
        day_name = item["day"]
        if cur_date:
            date_str = cur_date.strftime("%Y-%m-%d")
            lines.append(f"== {day_name} ({date_str}) ==")
            cur_date += timedelta(days=1)
        else:
            lines.append(f"= {day_name}")
        
        lines.append("")

        dishes = item["dishes"]
        for j, dish in enumerate(dishes):
            trailing = " \\" if j < len(dishes) - 1 else ""
            lines.append(f"@./{dish}{servings_str}{trailing}")

        lines.append("")

    return "\n".join(lines).strip() + "\n"

def main():
    parser = argparse.ArgumentParser(description="Generate Cooklang .menu file with random balanced recipes.")
    parser.add_argument("-o", "--output", default=None, help="Output file path (default: menus/<next_monday>.menu)")
    parser.add_argument("-m", "--menus-dir", default="menus", help="Directory for storing menu files (default: menus)")
    parser.add_argument("-d", "--date", default=None, help="Base date (YYYY-MM-DD) to calculate next Monday from (defaults to today)")
    parser.add_argument("-s", "--servings", default=None, help="Optional scale / servings number (e.g. 2)")
    parser.add_argument("-n", "--days", type=int, default=7, help="Number of days to generate (default: 7)")
    parser.add_argument("--dir", default=".", help="Directory containing .cook recipe files (default: current dir)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible results")
    parser.add_argument("-f", "--force", action="store_true", help="Force overwrite if menu file already exists")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # 1. Determine target date (next Monday)
    next_monday = get_next_monday(args.date)
    date_str = next_monday.strftime("%Y-%m-%d")

    # 2. Determine target file path
    if args.output:
        target_path = args.output
    else:
        menus_dir = os.path.join(args.dir, args.menus_dir)
        os.makedirs(menus_dir, exist_ok=True)
        target_path = os.path.join(menus_dir, f"{date_str}.menu")

    # 3. Check if file already exists
    if os.path.exists(target_path) and not args.force:
        print(f"菜单文件已存在，无需重复生成: {target_path}")
        return

    # 4. Scan and categorize .cook files
    categories = load_and_categorize_recipes(args.dir)
    print(f"已加载菜谱库: {len(categories['主食'])} 主食, {len(categories['肉菜'])} 肉菜, {len(categories['素菜'])} 素菜, {len(categories['零食'])} 零食")

    if not categories["主食"] or not categories["肉菜"] or not categories["素菜"]:
        print("错误: 缺少必要类别的菜谱（主食、肉菜、素菜）。")
        return

    # 5. Randomly select balanced meals
    menu_plan = build_random_menu(categories, days=args.days)

    # 6. Format as official Cooklang menu
    content = format_cooklang_menu(menu_plan, start_date=next_monday, servings=args.servings)

    # Ensure parent dir exists
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"成功生成下周一（{date_str}）的儿童菜单: {target_path}")

if __name__ == "__main__":
    main()

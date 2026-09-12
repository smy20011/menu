#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
All-in-one Cooklang Weekly Menu & Report Pipeline:
1. Calculates the upcoming Monday (YYYY-MM-DD).
2. Generates `menus/YYYY-MM-DD.menu` with random, non-repeating dishes (if not already present).
3. Combines Shopping List FIRST, then Weekly Menu into a single clean Markdown file:
   `reports/YYYY-MM-DD.md` (no horizontal dividers).
Fails fast on any error without suppressing exceptions.
"""

import os
import glob
import json
import random
import argparse
import subprocess
from datetime import datetime, timedelta, date

DAYS_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def get_next_monday(base_date=None):
    if base_date is None:
        base_date = date.today()
    elif isinstance(base_date, str):
        base_date = datetime.strptime(base_date, "%Y-%m-%d").date()

    days_ahead = (0 - base_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base_date + timedelta(days=days_ahead)

def load_and_categorize_recipes(recipes_dir="."):
    categories = {"主食": [], "肉菜": [], "素菜": [], "零食": []}
    cook_files = glob.glob(os.path.join(recipes_dir, "*.cook"))
    
    for f in cook_files:
        res = subprocess.run(
            ["cook", "recipe", "--format", "json", f],
            capture_output=True, text=True, check=True
        )

        data = json.loads(res.stdout)
        tags = data["metadata"]["map"].get("tags", [])
        recipe_name = os.path.splitext(os.path.basename(f))[0]

        matched = False
        for cat in categories.keys():
            if cat in tags:
                categories[cat].append(recipe_name)
                matched = True

        if not matched:
            categories["素菜"].append(recipe_name)

    return categories

def build_random_menu(categories, days=7, include_snack_on_weekends=True):
    staples_pool = list(categories["主食"])
    meats_pool = list(categories["肉菜"])
    veggies_pool = list(categories["素菜"])
    snacks_pool = list(categories["零食"])

    random.shuffle(staples_pool)
    random.shuffle(meats_pool)
    random.shuffle(veggies_pool)
    random.shuffle(snacks_pool)

    menu_plan = []
    for i in range(days):
        day_name = DAYS_ZH[i % len(DAYS_ZH)]
        
        if not staples_pool:
            staples_pool = list(categories["主食"])
            random.shuffle(staples_pool)
        if not meats_pool:
            meats_pool = list(categories["肉菜"])
            random.shuffle(meats_pool)
        if not veggies_pool:
            veggies_pool = list(categories["素菜"])
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

def generate_combined_report(menu_path, base_dir="."):
    menu_basename = os.path.basename(menu_path)
    date_prefix = os.path.splitext(menu_basename)[0]
    
    templates_dir = os.path.join(base_dir, "templates")
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    combined_report_path = os.path.join(reports_dir, f"{date_prefix}.md")

    # 1. Shopping List first via `cook shopping-list --format json`
    cmd_shop = ["cook", "shopping-list", "--format", "json", menu_path]
    res_shop = subprocess.run(cmd_shop, cwd=base_dir, capture_output=True, text=True, check=True)

    categories_data = json.loads(res_shop.stdout)

    shop_md_lines = [
        "# 每周食材采购清单",
        ""
    ]

    for cat in categories_data:
        cat_name = cat["category"]
        items = cat["items"]
        
        valid_names = []
        seen = set()
        for it in items:
            name = it["name"]
            if name not in seen:
                seen.add(name)
                valid_names.append(name)

        if not valid_names:
            continue

        header_name = "其他品类" if cat_name == "other" else cat_name
        shop_md_lines.append(f"### {header_name}")
        shop_md_lines.append("")
        for name in valid_names:
            shop_md_lines.append(f"- [ ] {name}")
        shop_md_lines.append("")

    # 2. Weekly Menu second via `cook report`
    menu_tmpl = os.path.join(templates_dir, "weekly_menu.md.j2")
    cmd_menu = ["cook", "report", "--template", menu_tmpl, menu_path]
    res_menu = subprocess.run(cmd_menu, cwd=base_dir, capture_output=True, text=True, check=True)
    clean_menu = "\n".join([l for l in res_menu.stdout.splitlines() if not l.startswith(" WARN") and not l.startswith("Warning:")])

    # Combine: Shopping list first, then Menu, no dividers
    combined_content = "\n".join(shop_md_lines).strip() + "\n\n" + clean_menu.strip() + "\n"

    with open(combined_report_path, "w", encoding="utf-8") as f:
        f.write(combined_content)

    print(f"✅ 已生成购物列表在前、菜单在后的合并文件: {combined_report_path}")

def main():
    parser = argparse.ArgumentParser(description="Cooklang all-in-one menu and reports pipeline.")
    parser.add_argument("-o", "--output", default=None, help="Output file path (default: menus/<next_monday>.menu)")
    parser.add_argument("-m", "--menus-dir", default="menus", help="Directory for storing menu files (default: menus)")
    parser.add_argument("-d", "--date", default=None, help="Base date (YYYY-MM-DD) to calculate next Monday from")
    parser.add_argument("-s", "--servings", default=None, help="Optional scale / servings number (e.g. 2)")
    parser.add_argument("-n", "--days", type=int, default=7, help="Number of days to generate (default: 7)")
    parser.add_argument("--dir", default=".", help="Directory containing .cook recipe files (default: current dir)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible results")
    parser.add_argument("-f", "--force", action="store_true", help="Force overwrite if menu file already exists")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    next_monday = get_next_monday(args.date)
    date_str = next_monday.strftime("%Y-%m-%d")

    if args.output:
        target_path = args.output
    else:
        menus_dir = os.path.join(args.dir, args.menus_dir)
        os.makedirs(menus_dir, exist_ok=True)
        target_path = os.path.join(menus_dir, f"{date_str}.menu")

    # Step 1: Menu Generation
    if os.path.exists(target_path) and not args.force:
        print(f"菜单文件已存在，跳过新建，直接更新对应合并报告: {target_path}")
    else:
        categories = load_and_categorize_recipes(args.dir)
        print(f"通过 cook CLI (JSON模式) 加载菜谱: {len(categories['主食'])} 主食, {len(categories['肉菜'])} 肉菜, {len(categories['素菜'])} 素菜, {len(categories['零食'])} 零食")

        if not categories["主食"] or not categories["肉菜"] or not categories["素菜"]:
            raise RuntimeError("缺少必要类别的菜谱（主食、肉菜、素菜）。")

        menu_plan = build_random_menu(categories, days=args.days)
        content = format_cooklang_menu(menu_plan, start_date=next_monday, servings=args.servings)

        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"成功生成下周一（{date_str}）的儿童菜单: {target_path}")

    # Step 2: Combined Report Generation (Shopping list first, then menu)
    generate_combined_report(target_path, base_dir=args.dir)

if __name__ == "__main__":
    main()

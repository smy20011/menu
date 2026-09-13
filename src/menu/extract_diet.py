#!/usr/bin/env python3
"""
从 B 站 UP 主空间提取减脂食谱，解析菜品、来源视频并智能推测所需食材，
最终生成标准的 Cooklang (.cook) 食谱文件并存入 diet 目录。
This one is fully AI generated.
"""

import argparse
from dataclasses import dataclass, field
import hashlib
import http.cookiejar
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

COOKIE_FILE = "/home/deck/Downloads/www.bilibili.com_cookies.txt"
MID = 313924270
PAGE_SIZE = 30

# B站 Wbi 混淆索引表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

PROTEIN_RULES = [
    ("鸡腿", ("去皮鸡腿肉", "150", "g")),
    ("鸡胸", ("鸡胸肉", "150", "g")),
    ("鸡翅", ("鸡翅中", "150", "g")),
    ("鸡排", ("去皮鸡腿肉", "150", "g")),
    ("鸡肉", ("去皮鸡腿肉", "150", "g")),
    ("鸡", ("去皮鸡腿肉", "150", "g")),
    ("肥牛", ("肥牛卷", "120", "g")),
    ("牛排", ("牛排肉", "150", "g")),
    ("牛腩", ("牛腩块", "120", "g")),
    ("牛肉", ("牛里脊肉", "120", "g")),
    ("牛", ("牛里脊肉", "120", "g")),
    ("肉末", ("牛绞肉", "100", "g")),
    ("肉酱", ("牛绞肉", "100", "g")),
    ("肉碎", ("牛绞肉", "100", "g")),
    ("肉沫", ("牛绞肉", "100", "g")),
    ("肉丝", ("牛里脊肉", "100", "g")),
    ("肉片", ("牛里脊肉", "100", "g")),
    ("小炒肉", ("牛里脊肉", "100", "g")),
    ("炒肉", ("牛里脊肉", "100", "g")),
    ("排骨", ("牛小排", "150", "g")),
    ("瘦肉", ("牛里脊肉", "100", "g")),
    ("五花肉", ("肥牛卷", "100", "g")),
    ("五花", ("肥牛卷", "100", "g")),
    ("猪肉", ("牛里脊肉", "100", "g")),
    ("猪", ("牛里脊肉", "100", "g")),
    ("虾滑", ("鲜虾滑", "100", "g")),
    ("虾仁", ("鲜虾仁", "100", "g")),
    ("虾片", ("鲜虾仁", "100", "g")),
    ("鲜虾", ("鲜虾仁", "100", "g")),
    ("大虾", ("鲜虾仁", "100", "g")),
    ("虾", ("鲜虾仁", "100", "g")),
    ("三文鱼", ("三文鱼柳", "120", "g")),
    ("鳕鱼", ("银鳕鱼", "120", "g")),
    ("鲈鱼", ("鲜鲈鱼柳", "150", "g")),
    ("龙利鱼", ("龙利鱼柳", "150", "g")),
    ("巴沙鱼", ("巴沙鱼柳", "150", "g")),
    ("鱼片", ("鲜鱼片", "150", "g")),
    ("鱼", ("鲜鱼片", "150", "g")),
    ("滑蛋", ("鸡蛋", "2", "个")),
    ("抱蛋", ("鸡蛋", "2", "个")),
    ("荷包蛋", ("鸡蛋", "2", "个")),
    ("炒蛋", ("鸡蛋", "2", "个")),
    ("煎蛋", ("鸡蛋", "2", "个")),
    ("爆蛋", ("鸡蛋", "2", "个")),
    ("蛋", ("鸡蛋", "2", "个")),
    ("豆腐", ("嫩豆腐", "150", "g")),
]

VEGGIE_RULES = [
    ("冬瓜", ("冬瓜", "200", "g")),
    ("口蘑", ("口蘑", "5", "朵")),
    ("香菇", ("鲜香菇", "4", "朵")),
    ("金针菇", ("金针菇", "100", "g")),
    ("杏鲍菇", ("杏鲍菇", "100", "g")),
    ("菌菇", ("菌菇组合", "100", "g")),
    ("蘑菇", ("口蘑", "4", "朵")),
    ("裙带菜", ("裙带菜", "5", "g")),
    ("海带", ("海带苗", "50", "g")),
    ("贡菜", ("贡菜", "50", "g")),
    ("西兰花", ("西兰花", "100", "g")),
    ("花菜", ("白花椰菜", "100", "g")),
    ("花椰菜", ("白花椰菜", "100", "g")),
    ("黄瓜", ("黄瓜", "1", "根")),
    ("番茄", ("熟番茄", "1", "个")),
    ("西红柿", ("熟番茄", "1", "个")),
    ("茄汁", ("熟番茄", "1", "个")),
    ("土豆", ("土豆", "150", "g")),
    ("娃娃菜", ("娃娃菜", "150", "g")),
    ("包菜", ("包菜", "150", "g")),
    ("卷心菜", ("卷心菜", "150", "g")),
    ("圆白菜", ("圆白菜", "150", "g")),
    ("大白菜", ("大白菜", "150", "g")),
    ("白菜", ("大白菜", "150", "g")),
    ("菠菜", ("菠菜", "150", "g")),
    ("生菜", ("生菜", "100", "g")),
    ("油麦菜", ("油麦菜", "150", "g")),
    ("胡萝卜", ("胡萝卜", "50", "g")),
    ("玉米", ("甜玉米粒", "50", "g")),
    ("洋葱", ("洋葱", "50", "g")),
    ("青椒", ("青椒", "1", "个")),
    ("彩椒", ("彩椒", "1", "个")),
    ("茄子", ("圆茄子", "150", "g")),
    ("地三鲜", ("圆茄子", "150", "g")),
    ("西葫芦", ("西葫芦", "150", "g")),
    ("节瓜", ("西葫芦", "150", "g")),
    ("栉瓜", ("西葫芦", "150", "g")),
    ("豆芽", ("绿豆芽", "100", "g")),
    ("芦笋", ("鲜芦笋", "100", "g")),
    ("荷兰豆", ("荷兰豆", "80", "g")),
    ("毛豆", ("毛豆仁", "50", "g")),
    ("南瓜", ("贝贝南瓜", "150", "g")),
    ("红薯", ("红薯", "150", "g")),
    ("地瓜", ("红薯", "150", "g")),
    ("紫薯", ("紫薯", "150", "g")),
    ("苦瓜", ("苦瓜", "150", "g")),
    ("丝瓜", ("丝瓜", "150", "g")),
    ("藕", ("莲藕", "100", "g")),
]

STAPLE_RULES = [
    ("乌冬", ("乌冬面", "100", "g")),
    ("意面", ("意大利面", "70", "g")),
    ("荞麦", ("荞麦面", "60", "g")),
    ("焖面", ("全麦面条", "60", "g")),
    ("拌面", ("全麦面条", "60", "g")),
    ("汤面", ("全麦面条", "60", "g")),
    ("炒面", ("全麦面条", "60", "g")),
    ("面", ("全麦面条", "60", "g")),
    ("燕麦", ("快熟燕麦片", "40", "g")),
    ("饺", ("饺子皮", "8", "张")),
    ("卷饼", ("全麦卷饼", "1", "张")),
    ("手抓饼", ("全麦卷饼", "1", "张")),
    ("吐司", ("全麦吐司", "2", "片")),
    ("面包", ("全麦吐司", "2", "片")),
    ("贝果", ("全麦贝果", "1", "个")),
    ("粉丝", ("绿豆粉丝", "40", "g")),
    ("米线", ("米线", "60", "g")),
    ("饭包", ("生菜大米饭", "150", "g")),
    ("盖饭", ("杂粮米饭", "130", "g")),
    ("拌饭", ("杂粮米饭", "130", "g")),
    ("焖饭", ("杂粮米饭", "130", "g")),
    ("炒饭", ("杂粮米饭", "130", "g")),
    ("烩饭", ("杂粮米饭", "130", "g")),
    ("饭", ("杂粮米饭", "130", "g")),
    ("粥", ("大米粥", "200", "g")),
]

SPECIAL_RULES = {
    "地三鲜": [("土豆", "100", "g"), ("圆茄子", "100", "g"), ("青椒", "1", "个")],
    "大饭包": [("生菜", "100", "g"), ("熟米饭", "130", "g"), ("土豆", "100", "g"), ("鸡蛋", "1", "个")],
    "公瑾爆蛋": [("鸡蛋", "3", "个"), ("生抽", "1", "大勺"), ("食用油", "1", "茶匙")],
}


@dataclass
class DietRecipe:
    title: str
    source_url: str
    meal_type: str
    category: str
    calories: str | None
    ingredients: list[tuple[str, str, str]] = field(default_factory=list)

    def to_cooklang(self) -> str:
        tags = ["减肥餐", self.meal_type, self.category]
        if self.calories:
            tags.append(self.calories)

        lines = [
            "---",
            f"title: {self.title}",
            "tags:",
        ]
        for t in tags:
            lines.append(f"  - {t}")
        lines.append("servings: 1")
        lines.append(f"source: {self.source_url}")
        lines.append("---")
        lines.append("")
        for name, qty, unit in self.ingredients:
            lines.append(f"@{name}{{{qty}%{unit}}}")
        lines.append("")
        return "\n".join(lines)


def get_opener(cookie_path: str) -> urllib.request.OpenerDirector:
    cj = http.cookiejar.MozillaCookieJar(cookie_path)
    cj.load(ignore_discard=True, ignore_expires=True)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        ("Referer", f"https://space.bilibili.com/{MID}/upload/video"),
    ]
    return opener


def get_wbi_mixin_key(opener: urllib.request.OpenerDirector) -> str:
    resp = opener.open("https://api.bilibili.com/x/web-interface/nav").read()
    wbi_img = json.loads(resp)["data"]["wbi_img"]
    img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
    raw_key = img_key + sub_key
    return "".join([raw_key[n] for n in MIXIN_KEY_ENC_TAB])[:32]


def guess_ingredients(dish_name: str) -> tuple[str, list[tuple[str, str, str]]]:
    """根据菜名智能推测食材并推断所属分类（主食/肉菜/素菜/汤品/早餐）"""
    added_names = set()
    ingredients = []

    # 1. 检查特殊组合
    for key, items in SPECIAL_RULES.items():
        if key in dish_name:
            for item in items:
                if item[0] not in added_names:
                    ingredients.append(item)
                    added_names.add(item[0])

    # 2. 匹配蛋白质 (肉类、蛋类、豆制品)
    has_protein = False
    for kw, ing in PROTEIN_RULES:
        if kw in dish_name and not (kw == "鸡" and "鸡蛋" in dish_name) and ing[0] not in added_names:
            ingredients.append(ing)
            added_names.add(ing[0])
            has_protein = True
            break  # 避免多重同质肉类混淆，取最高优先级

    # 3. 匹配蔬菜与菌菇
    has_veggie = False
    for kw, ing in VEGGIE_RULES:
        if kw in dish_name and ing[0] not in added_names:
            ingredients.append(ing)
            added_names.add(ing[0])
            has_veggie = True

    # 4. 匹配主食
    has_staple = False
    for kw, ing in STAPLE_RULES:
        if kw in dish_name and ing[0] not in added_names:
            ingredients.append(ing)
            added_names.add(ing[0])
            has_staple = True
            break

    # 5. 补充基本原料与调味料
    is_sweet_breakfast = any(k in dish_name for k in ["燕麦碗", "酸奶", "水果碗", "贝果", "松饼", "三明治"])
    is_soup = "汤" in dish_name or "煲" in dish_name

    if is_sweet_breakfast:
        if "牛奶" not in added_names:
            ingredients.append(("低脂牛奶", "200", "ml"))
        if "香蕉" not in added_names and "蓝莓" not in added_names:
            ingredients.append(("香蕉", "1", "根"))
    else:
        # 减脂中式咸味菜标配：少油、生抽、食用盐
        if "食用油" not in added_names:
            ingredients.append(("食用油", "1", "茶匙"))
        if "生抽" not in added_names:
            ingredients.append(("生抽", "1", "大勺"))
        if "食用盐" not in added_names:
            ingredients.append(("食用盐", "1", "g"))

        if is_soup and "水" not in added_names:
            ingredients.append(("水", "300", "ml"))
        elif any(k in dish_name for k in ["焖", "炖", "烩"]) and "水" not in added_names:
            ingredients.append(("水", "50", "ml"))

        if "黑椒" in dish_name and "黑胡椒碎" not in added_names:
            ingredients.append(("黑胡椒碎", "0.5", "茶匙"))
        if any(k in dish_name for k in ["蒜", "蒜香"]) and "大蒜" not in added_names:
            ingredients.append(("大蒜", "2", "瓣"))
        if any(k in dish_name for k in ["葱", "葱烧", "大葱"]) and "大葱" not in added_names:
            ingredients.append(("大葱", "10", "g"))
        if any(k in dish_name for k in ["酸辣", "柠檬"]) and "柠檬" not in added_names:
            ingredients.append(("柠檬", "2", "片"))

    # 兜底：如果食材过少（例如仅有基础调料），按减脂常用时蔬补充
    if not (has_protein or has_veggie or has_staple):
        ingredients.insert(0, ("时令蔬菜", "150", "g"))

    # 分类推断
    if is_soup:
        category = "汤品"
    elif has_staple or any(k in dish_name for k in ["饭", "面", "粥", "饺", "饼"]):
        category = "主食"
    elif has_protein:
        category = "肉菜"
    else:
        category = "素菜"

    return category, ingredients


def parse_video_item(bvid: str, title: str) -> list[DietRecipe]:
    """从单个视频标题解析一道或多道菜品"""
    url = f"https://www.bilibili.com/video/{bvid}"

    # 1. 提取卡路里
    cal_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:千卡|kcal)", title, re.I)
    calories = f"{int(float(cal_m.group(1)))}千卡" if cal_m else None

    # 2. 提取餐别
    meal_type = "午餐"
    if "早餐" in title:
        meal_type = "早餐"
    elif "晚餐" in title:
        meal_type = "晚餐"
    elif any(k in title for k in ["全天", "一日", "两餐"]):
        meal_type = "全天饮食"

    # 3. 提取菜名
    m_old = re.search(r"今日(?:午餐|晚餐|食谱|早餐|两餐)[—\-]([^\s\d千卡kcal，,。！!]+)", title)
    if m_old:
        dish_core = m_old.group(1)
    else:
        clean = re.sub(r"^【.*?】", "", title).strip()
        parts = [p.strip() for p in re.split(r"[｜|]", clean) if p.strip()]
        if parts:
            dish_part = parts[-1]
            dish_core = re.split(r"[。！!，,\s]|(?:\d+\s*(?:千卡|kcal))", dish_part)[0].strip()
        else:
            dish_core = ""

    dish_core = re.sub(r"^(?:中式)?(?:减脂餐|自律餐|午餐|晚餐|早餐)[：:—\-\s]*", "", dish_core).strip()

    # 处理形如 "菜品A+菜品B+菜品C" 的组合
    sub_names = [d.strip() for d in dish_core.split("+") if d.strip()]
    recipes = []

    for name in sub_names:
        name = re.sub(r"^(?:一道适合.*?的)?(?:减脂餐|自律餐|午餐|晚餐|早餐)[：:—\-\s]*", "", name).strip()
        name = re.sub(r"^[：:｜|、\s—\-]+", "", name)
        name = re.sub(r"[\/\\:\*\?\"<>\|]", "", name)  # 过滤非法文件名字符

        if len(name) < 2 or name.startswith("靠吃瘦了") or name.startswith("三大营养素"):
            continue

        category, ingredients = guess_ingredients(name)
        recipe = DietRecipe(
            title=name,
            source_url=url,
            meal_type=meal_type,
            category=category,
            calories=calories,
            ingredients=ingredients,
        )
        recipes.append(recipe)

    return recipes


def fetch_all_diet_recipes(cookie_path: str, mid: int, max_pages: int = 0) -> list[DietRecipe]:
    opener = get_opener(cookie_path)
    mixin_key = get_wbi_mixin_key(opener)

    recipes: list[DietRecipe] = []
    seen_titles = set()
    page = 1
    total_count = None

    while True:
        curr_time = int(time.time())
        params = {
            "mid": mid,
            "ps": PAGE_SIZE,
            "tid": 0,
            "pn": page,
            "keyword": "",
            "order": "pubdate",
            "wts": curr_time,
        }
        clean_params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in params.items()}
        sorted_params = dict(sorted(clean_params.items()))
        query = urllib.parse.urlencode(sorted_params)
        w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()

        url = f"https://api.bilibili.com/x/space/wbi/arc/search?{query}&w_rid={w_rid}"
        resp_data = json.loads(opener.open(url).read()).get("data", {})

        if total_count is None:
            total_count = resp_data.get("page", {}).get("count", 0)
            print(f"B站 UP 主 (UID: {mid}) 视频总数: {total_count}")

        vlist = resp_data.get("list", {}).get("vlist", [])
        if not vlist:
            break

        for item in vlist:
            parsed = parse_video_item(item["bvid"], item["title"])
            for r in parsed:
                if r.title not in seen_titles:
                    seen_titles.add(r.title)
                    recipes.append(r)

        print(f"已处理第 {page} 页，已提取独立菜品: {len(recipes)} 道")

        if max_pages > 0 and page >= max_pages:
            break

        # 判断是否到达最后一页
        if page * PAGE_SIZE >= total_count:
            break

        page += 1
        time.sleep(0.3)

    return recipes


def save_recipes(recipes: list[DietRecipe], dest_dir: Path, force: bool = True) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0
    for r in recipes:
        filepath = dest_dir / f"{r.title}.cook"
        if filepath.exists() and not force:
            continue
        filepath.write_text(r.to_cooklang(), encoding="utf-8")
        saved_count += 1
    return saved_count


def main():
    parser = argparse.ArgumentParser(description="提取 B 站 UP 主减脂食谱并生成 Cooklang 文件")
    parser.add_argument("--cookie", default=COOKIE_FILE, help=f"Cookie 文件路径，默认: {COOKIE_FILE}")
    parser.add_argument("--dest", default="diet", help="生成的食谱存放目录，默认: diet")
    parser.add_argument("--mid", type=int, default=MID, help=f"UP 主 UID，默认: {MID}")
    parser.add_argument("--max-pages", type=int, default=0, help="最多抓取页数 (0 为抓取全部)")
    parser.add_argument("-f", "--force", action="store_true", default=True, help="是否覆盖已存在的同名菜谱")

    opts = parser.parse_args()
    dest_path = Path(opts.dest)

    print(f"正在从 B 站抓取并解析食谱...")
    recipes = fetch_all_diet_recipes(opts.cookie, opts.mid, opts.max_pages)
    saved = save_recipes(recipes, dest_path, opts.force)

    print(f"\n成功生成 {saved} 份减脂菜谱文件至目录: {dest_path.resolve()}/")
    print("每个菜谱均带有 '减肥餐' tag 与对应的餐别/食材列表。")


if __name__ == "__main__":
    main()

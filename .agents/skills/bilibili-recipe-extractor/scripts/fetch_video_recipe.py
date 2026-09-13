#!/usr/bin/env python3
"""
B站视频字幕与食谱信息直接提取工具。
通过 Cookie + Wbi 签名直接拉取视频官方/AI 字幕文本，无需下载音视频或本地 ASR。
"""

import argparse
import hashlib
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

COOKIE_FILE = "/home/deck/Downloads/www.bilibili.com_cookies.txt"

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def extract_bvid(target: str) -> str:
    m = re.search(r"(BV[0-9a-zA-Z]{10})", target)
    if not m:
        raise ValueError(f"无法识别有效的 BVID: {target}")
    return m.group(1)


def get_opener(cookie_path: str, referer: str) -> urllib.request.OpenerDirector:
    cj = http.cookiejar.MozillaCookieJar(cookie_path)
    if Path(cookie_path).exists():
        cj.load(ignore_discard=True, ignore_expires=True)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        ("Referer", referer),
    ]
    return opener


def get_wbi_keys(opener: urllib.request.OpenerDirector) -> str:
    nav_resp = opener.open("https://api.bilibili.com/x/web-interface/nav").read()
    wbi_img = json.loads(nav_resp)["data"]["wbi_img"]
    img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
    sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
    raw_key = img_key + sub_key
    return "".join([raw_key[n] for n in MIXIN_KEY_ENC_TAB])[:32]


def fetch_video_details(bvid: str, cookie_path: str = COOKIE_FILE) -> dict:
    url = f"https://www.bilibili.com/video/{bvid}"
    opener = get_opener(cookie_path, url)

    # 1. 视频基本信息
    view_data = json.loads(opener.open(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}").read())["data"]
    title = view_data.get("title", "")
    desc = view_data.get("desc", "")
    aid = view_data.get("aid")
    cid = view_data.get("cid")
    duration = view_data.get("duration", 0)

    # 2. 获取 Wbi 密钥
    mixin_key = get_wbi_keys(opener)

    # 3. 签名并请求 /x/player/wbi/v2
    params = {"aid": aid, "cid": cid, "wts": int(time.time())}
    clean_params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(dict(sorted(clean_params.items())))
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()

    v2_url = f"https://api.bilibili.com/x/player/wbi/v2?{query}&w_rid={w_rid}"
    v2_data = json.loads(opener.open(v2_url).read())["data"]
    subtitles_list = v2_data.get("subtitle", {}).get("subtitles", [])

    subtitles = []
    if subtitles_list:
        sub_url = subtitles_list[0]["subtitle_url"]
        if sub_url.startswith("//"):
            sub_url = "https:" + sub_url
        sub_data = json.loads(opener.open(sub_url).read())
        for item in sub_data.get("body", []):
            subtitles.append({
                "from": item.get("from", 0.0),
                "to": item.get("to", 0.0),
                "text": item.get("content", "").strip(),
            })

    return {
        "bvid": bvid,
        "url": url,
        "title": title,
        "description": desc,
        "duration": duration,
        "subtitles": subtitles,
        "full_text": " ".join(s["text"] for s in subtitles),
    }


def main():
    parser = argparse.ArgumentParser(description="提取 B 站视频元数据与真实字幕")
    parser.add_argument("target", help="视频链接或 BVID，例如 BV1iFQEY7ED7")
    parser.add_argument("--cookie", default=COOKIE_FILE, help=f"Cookie 路径，默认: {COOKIE_FILE}")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    args = parser.parse_args()
    bvid = extract_bvid(args.target)

    data = fetch_video_details(bvid, args.cookie)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"=== 视频标题: {data['title']} ===")
        print(f"BVID: {data['bvid']} | 时长: {data['duration']} 秒 | 字幕行数: {len(data['subtitles'])}")
        print("\n--- 完整字幕文本 ---")
        print(data["full_text"])


if __name__ == "__main__":
    main()

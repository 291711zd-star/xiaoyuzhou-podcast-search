# -*- coding: utf-8 -*-
"""
抓取「播客良品铺子」周榜单集，生成 data.js（小宇宙热门单集前 N 名）。

用法：
    python3 scrape_chart.py [榜单单集链接] [取前几名]

例子：
    python3 scrape_chart.py            # 用默认榜单，取前 50 名
    python3 scrape_chart.py https://www.xiaoyuzhoufm.com/episode/xxxx 50

原理：榜单单集的 shownotes（节目介绍）里，每条排名都是
「名次｜播客名｜单集标题」的格式，标题本身是跳往该单集的链接，
本脚本把名次、播客名、标题、链接一条条抠出来，写成 data.js 给页面用。
"""

import re
import sys
import json
import html as html_lib
import urllib.request

# 默认榜单：第 89 期播客周榜（11.2–11.8）；有新一期时把链接换掉即可
DEFAULT_CHART_URL = "https://www.xiaoyuzhoufm.com/episode/6af419ba14d01a26f8a84099"

chart_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CHART_URL
top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 50

# 1) 把榜单页面的 HTML（网页源代码）下载下来
req = urllib.request.Request(chart_url, headers={"User-Agent": "Mozilla/5.0"})
page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")

# 2) 抠出榜单信息：期号、统计周期、发布日期
title_match = re.search(r"<title>(.*?)</title>", page, re.S)
page_title = html_lib.unescape(title_match.group(1)) if title_match else ""
issue_match = re.search(r"(\d+)\s*播客周榜", page_title)
period_match = re.search(r"（([\d.\-–]+)）", page_title)
date_match = re.search(r'"datePublished":"([\d\-]+)', page)
meta = {
    "issue": issue_match.group(1) if issue_match else "?",
    "period": period_match.group(1) if period_match else "",
    "published": date_match.group(1) if date_match else "",
    "chart_url": chart_url,
}

# 3) 一条条抠出排名数据
# 页面结构：<span>名次｜播客名｜</span><a href="单集链接"><span>单集标题</span></a>
pattern = re.compile(
    r"<span>(\d+)｜(.*?)</span><a href=\"(https://www\.xiaoyuzhoufm\.com/episode/[0-9a-f]+)\"[^>]*>(.*?)</a>",
    re.S,
)
by_rank = {}
for rank, name_part, url, raw_title in pattern.findall(page):
    rank = int(rank)
    podcast = name_part.strip().rstrip("｜").strip()
    title = html_lib.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
    if rank not in by_rank:  # 同一名次只留第一次出现的
        by_rank[rank] = {"rank": rank, "podcast": podcast, "title": title, "url": url}

episodes = [by_rank[r] for r in sorted(by_rank)][:top_n]
if len(episodes) < top_n:
    print(f"警告：只抓到 {len(episodes)} 条，少于想要的 {top_n} 条", file=sys.stderr)

# 4) 写成 data.js，供 index.html 读取
out = (
    "// 本文件由 scrape_chart.py 自动生成，请勿手改；要更新数据请重新运行脚本\n"
    f"const CHART_META = {json.dumps(meta, ensure_ascii=False)};\n"
    f"const EPISODES = {json.dumps(episodes, ensure_ascii=False, indent=2)};\n"
)
with open("data.js", "w", encoding="utf-8") as f:
    f.write(out)

print(f"完成：第 {meta['issue']} 期周榜（{meta['period']}），共写入 {len(episodes)} 条到 data.js")
for ep in episodes[:3]:
    print(f"  第{ep['rank']}名｜{ep['podcast']}｜{ep['title']}")

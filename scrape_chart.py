# -*- coding: utf-8 -*-
"""
抓取「播客良品铺子」最新一期《播客周榜》，生成 data.js（小宇宙热门单集前 N 名）。

用法：
    python3 scrape_chart.py              # 自动找最新一期周榜，取前 50 名
    python3 scrape_chart.py 30           # 自动找最新一期周榜，取前 30 名
    python3 scrape_chart.py <榜单链接>   # 指定某一期榜单，取前 50 名

原理：
1) 先去「播客良品铺子」主页，找出最新一期《播客周榜》的单集链接；
2) 打开那期榜单，它的 shownotes（节目介绍）里每条排名都是
   「名次｜播客名｜单集标题」的格式，标题本身是跳往该单集的链接；
3) 把名次、播客名、标题、链接一条条抠出来，写成 data.js 给页面用。
"""

import re
import sys
import json
import html as html_lib
import urllib.request

# 「播客良品铺子」主页：最新一期周榜从这里找
PODCAST_URL = "https://www.xiaoyuzhoufm.com/podcast/69ee56b9f4ff26e89f48037f"
DEFAULT_TOP_N = 50


def fetch(url):
    """把一个网页的 HTML（源代码）下载下来"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def find_latest_chart_url():
    """去播客主页，找出期号最大的那期《播客周榜》的链接"""
    page = fetch(PODCAST_URL)
    candidates = []
    # 主页源码里每期节目都有一段 "eid":"单集编号","pid":"播客编号","title":"标题"
    for eid, raw_title in re.findall(
        r'"eid":"([0-9a-f]+)","pid":"[0-9a-f]+","title":"([^"]+)"', page
    ):
        m = re.match(r"(\d+)\s*播客周榜", html_lib.unescape(raw_title))
        if m:  # 标题长这样：「93 播客周榜｜本周热门单集TOP150 （11.9-11.15）」
            candidates.append((int(m.group(1)), eid))
    if not candidates:
        raise RuntimeError("在播客主页没找到《播客周榜》，可能页面改版了")
    issue, eid = max(candidates)  # 期号最大的就是最新一期
    return issue, f"https://www.xiaoyuzhoufm.com/episode/{eid}"


def main():
    args = sys.argv[1:]
    if args and args[0].startswith("http"):
        chart_url = args[0]
        top_n = int(args[1]) if len(args) > 1 else DEFAULT_TOP_N
    else:
        top_n = int(args[0]) if args else DEFAULT_TOP_N
        issue, chart_url = find_latest_chart_url()
        print(f"自动找到最新周榜：第 {issue} 期 {chart_url}")

    # 1) 把榜单页面的 HTML 下载下来
    page = fetch(chart_url)

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


if __name__ == "__main__":
    main()

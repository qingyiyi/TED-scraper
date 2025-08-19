#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仅测试：由配置构造的 /talks URL 是否可达，以及解析结果
"""

import requests
from bs4 import BeautifulSoup
from ted_scraper_edge import TEDEdgeScraper
from config import TOPICS, SORT

def test_config_talks_url_access():
    scraper = TEDEdgeScraper()
    url = scraper.build_talks_url_from_config(TOPICS, sort=SORT)

    print(f"URL: {url}")

    print("=" * 60)
    print("        测试配置生成的 /talks URL 访问")
    print("=" * 60)
    print(f"URL: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
    }

    resp = requests.get(url, headers=headers, timeout=15)
    print(f"状态码: {resp.status_code}")
    print(f"页面大小: {len(resp.content)} 字节")
    
    # 保存HTML以排查
    # out_file = "ted_talks_config_test.html"
    # with open(out_file, 'w', encoding='utf-8') as f:
    #     f.write(resp.text)
    # print(f"页面已保存到: {out_file}")

    if resp.status_code != 200:
        print("❌ 访问失败")
        return

    # 测试JSON提取
    scraper = TEDEdgeScraper()
    videos = scraper._extract_talks_from_json(resp.text)
    print(f"JSON提取到 {len(videos)} 个视频")
    for i, v in enumerate(videos[:3], 1):
        print(f"{i}. {v.title} - {v.speaker} ({v.duration}) - {v.views}")

if __name__ == "__main__":
    test_config_talks_url_access()

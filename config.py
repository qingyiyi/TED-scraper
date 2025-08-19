#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TED视频筛选配置文件
"""

# 搜索主题列表
TOPICS = [
    "aging", 
    "communication", 
    "compassion",
    "creativity",
    "curiosity",
    "death",
    "depression",
    "emotions",
    "empathy",
    "ethics",
    "fear",
    "happiness",
    "love",
    "mental health",
    "mindfulness",
    "motivation",
    "personal growth",
    "sex",
    "sleep",
    "trust",
    "vulnerability"
]

# 时间筛选范围，ted只提供newest和oldest两种排列方式，当需要古老视频的时候，搜索页数需要设置的非常大，否则可能导致前10页并没有2018~2022年的视频
START_YEAR = 2018
END_YEAR = 2022

# 时长筛选范围（分钟）
MIN_DURATION = 12
MAX_DURATION = 18


# 获取前N和后N的视频数量
TOP_VIDEOS_COUNT = 100    # top与bottom数值要一致,当前版本需一致
BOTTOM_VIDEOS_COUNT = 100

# 请求延迟设置（秒）
REQUEST_DELAY = 1
TOPIC_DELAY = 2

# 输出文件名
OUTPUT_FILENAME = "ted_videos_results.xlsx"

# /talks 搜索参数排序方式，目前是从全部视频搜索，排序暂无影响，未来可以拓展为newest排序获取前100个，oldest排序获取前100个加快搜索速度
# newest 或 oldest
SORT = "newest"

# 浏览器设置
BROWSER_HEADLESS = True  # 是否使用无头模式
BROWSER_WINDOW_SIZE = "1920,1080"

# 日志级别
LOG_LEVEL = "INFO"

# 忽略SSL错误（解决握手失败问题）
EDGE_IGNORE_SSL_ERRORS = True

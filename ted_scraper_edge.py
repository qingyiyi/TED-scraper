#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TED视频筛选和文稿获取程序 - Edge浏览器版本
功能：
1. 根据主题、时长、发布时间(2018-2022)筛选视频
2. 获取播放量前100和后100的视频
3. 提取这些视频的演讲文稿
"""

import requests
import time
import json
import re
import argparse
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import logging
import os
import urllib.parse
from config import TOPICS, START_YEAR, END_YEAR, MIN_DURATION, MAX_DURATION, OUTPUT_FILENAME, SORT, TOP_VIDEOS_COUNT

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TEDVideo:
    """TED视频数据结构"""
    title: str
    speaker: str
    duration: str
    views: int
    publish_date: str
    topic: str
    url: str
    transcript: str = ""
    id: str = ""  # 添加ID用于更可靠的去重

class TEDEdgeScraper:
    """TED视频爬取器 - Edge浏览器版本"""
    
    def __init__(self):
        self.base_url = "https://www.ted.com"
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
        })
        
    def setup_driver(self):
        """设置Edge浏览器驱动"""
        try:
            edge_options = Options()
            edge_options.add_argument("--headless")  # 无头模式
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--window-size=1920,1080")
            edge_options.add_argument("--ignore-certificate-errors")  # 添加此行解决SSL问题
            
            # 尝试多种方式设置驱动
            driver_path = None
            
            # 方法1：尝试自动下载Edge驱动
            try:
                logger.info("尝试自动下载Edge驱动...")
                service = Service(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=edge_options)
                logger.info("Edge驱动自动下载成功")
                return
            except Exception as e:
                logger.warning(f"自动下载失败: {e}")
            
            # 方法2：尝试使用本地Edge驱动文件
            local_drivers = [
                "./msedgedriver.exe",  # Windows Edge驱动
                "./drivers/msedgedriver.exe",
                "./edgedriver.exe",
                "./drivers/edgedriver.exe",
                "D:/Drivers/edgedriver_win32/msedgedriver.exe"
            ]
            
            for driver_path in local_drivers:
                if os.path.exists(driver_path):
                    try:
                        logger.info(f"使用本地Edge驱动: {driver_path}")
                        service = Service(driver_path)
                        self.driver = webdriver.Edge(service=service, options=edge_options)
                        logger.info("Edge驱动设置成功")
                        return
                    except Exception as e:
                        logger.warning(f"本地Edge驱动 {driver_path} 加载失败: {e}")
                        continue
            
            # 方法3：尝试使用系统PATH中的Edge驱动
            try:
                logger.info("尝试使用系统PATH中的Edge驱动...")
                self.driver = webdriver.Edge(options=edge_options)
                logger.info("Edge驱动设置成功")
                return
            except Exception as e:
                logger.warning(f"系统PATH Edge驱动失败: {e}")
            
            # 所有方法都失败了
            raise Exception("无法设置Edge驱动，请手动下载并配置")
            
        except Exception as e:
            logger.error(f"设置Edge驱动失败: {e}")
            logger.error("请尝试以下解决方案：")
            logger.error("1. 手动下载Edge驱动并放在项目目录")
            logger.error("2. 检查网络连接和防火墙设置")
            logger.error("3. 使用简化版爬取器（不需要浏览器）")
            raise
    
    def close_driver(self):
        """关闭浏览器驱动"""
        if self.driver:
            self.driver.quit()
            logger.info("Edge驱动已关闭")
    

    def get_videos_by_talks_url(self, talks_url: str) -> List[TEDVideo]:
        """根据/talks URL抓取视频列表，直接从DOM提取数据"""
        if not self.driver:
            self.setup_driver()
        
        videos = []
        seen_urls = set()
        
        try:
            logger.info(f"开始抓取视频: {talks_url}")
            self.driver.get(talks_url)
            
            # 等待Cookie弹窗（如果存在）并关闭
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept all')]"))
                ).click()
                logger.info("成功关闭Cookie弹窗")
                time.sleep(1)  # 给页面一点时间响应
            except Exception as e:
                logger.debug(f"未找到Cookie弹窗: {e}")
            
            # 等待视频卡片加载
            logger.info("等待视频卡片加载...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.xs-tui\\:col-span-1 > a.relative[href*='/talks/']"))
            )
            logger.info("视频卡片已加载")
            
            # 等待视频卡片加载
            logger.info("等待视频卡片加载...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.xs-tui\\:col-span-1 > a.relative[href*='/talks/']"))
            )
            logger.info("视频卡片已加载")
            
            
            # === 获取总视频数并计算需要点击的次数 ===
            total_videos = 0
            try:
                # 提取"24 of n"中的总视频数
                count_element = self.driver.find_element(
                    By.CSS_SELECTOR, "p.text-textPrimary-onLight.font-normal.body2"
                )
                count_text = count_element.text
                logger.info(f"视频计数文本: {count_text}")
                
                # 使用正则提取总视频数
                match = re.search(r'of (\d+)', count_text)
                if match:
                    total_videos = int(match.group(1))
                    logger.info(f"总共有 {total_videos} 个视频")
                    
                    # 计算需要点击的次数（向上取整）
                    clicks_needed = (total_videos + 23) // 24 - 1
                    logger.info(f"需要点击 'Show 24 more' 按钮 {clicks_needed} 次")
                else:
                    logger.warning("无法从文本中提取总视频数")
                    total_videos = 0
            except Exception as e:
                logger.warning(f"无法获取总视频数: {e}")
            
            # 设置点击上限（防止网站错误导致无限点击）
            max_clicks = min(clicks_needed, 200) if total_videos > 0 else 50
            logger.info(f"设置点击上限为 {max_clicks} 次")
            
            # 点击"Show 24 more"按钮直到获取所有视频
            for i in range(max_clicks):
                try:
                    # 检查按钮是否存在
                    try:
                        load_more_button = self.driver.find_element(
                            By.XPATH, "//button//span[contains(text(), 'Show 24 more')]"
                        )
                    except:
                        logger.info("没有更多视频可加载，停止点击")
                        break
                    
                    # 滚动到按钮位置确保可见
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", 
                        load_more_button
                    )
                    time.sleep(0.5)
                    
                    # 尝试点击按钮
                    try:
                        load_more_button.click()
                        logger.info(f"成功点击 'Show 24 more' 按钮 (第 {i+1} 次)")
                    except:
                        # 如果直接点击失败，尝试使用JavaScript点击
                        self.driver.execute_script(
                            "arguments[0].click();", 
                            load_more_button
                        )
                        logger.info(f"使用JavaScript成功点击 'Show 24 more' 按钮 (第 {i+1} 次)")
                    
                    # 等待新内容加载
                    try:
                        WebDriverWait(self.driver, 10).until(
                            lambda d: len(d.find_elements(
                                By.CSS_SELECTOR, "div.xs-tui\\:col-span-1 > a.relative[href*='/talks/']")
                            ) > 24 * (i + 1)
                        )
                        logger.info(f"检测到新视频内容已加载")
                    except:
                        logger.warning("等待新内容加载超时，继续...")
                        time.sleep(3)
                    
                    # 验证新内容是否加载
                    current_count = len(self.driver.find_elements(
                        By.CSS_SELECTOR, "div.xs-tui\\:col-span-1 > a.relative[href*='/talks/']")
                    )
                    logger.info(f"当前已加载 {current_count} 个视频")
                    
                    # 检查是否已达到最大视频数
                    if total_videos > 0 and current_count >= total_videos:
                        logger.info("已加载所有视频，停止点击")
                        break
                        
                except Exception as e:
                    logger.warning(f"点击 'Show 24 more' 按钮失败 (第 {i+1} 次): {e}")
                    break


            # 找到所有视频卡片
            video_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.xs-tui\\:col-span-1 > a.relative[href*='/talks/']")
            logger.info(f"找到 {len(video_cards)} 个视频卡片元素")

            '''
            # === debug info: 在找到视频卡片后，保存完整JSON ===
            # 从页面源码中提取JSON数据
            html = self.driver.page_source
            # 保存HTML到文件
            with open('videos.html', 'w', encoding='utf-8') as f:
                f.write(html)
            '''

            for card in video_cards:
                try:
                    # 1. 提取URL
                    url = card.get_attribute('href')
                    if not url:
                        continue
                    if not url.startswith('http'):
                        url = self.base_url + url
                    
                    # 2. 提取标题
                    title = "未知标题"
                    try:
                        # 尝试主要标题选择器
                        title_elem = card.find_element(By.CSS_SELECTOR, "span.text-textPrimary-onLight.font-bold.subheader2")
                        title = title_elem.text.strip() or "未知标题"
                    except:
                        try:
                            # 备用选择器
                            title_elem = card.find_element(By.CSS_SELECTOR, "img[alt]")
                            title = title_elem.get_attribute('alt') or "未知标题"
                        except:
                            pass
                    
                    # 3. 提取演讲者
                    speaker = "未知演讲者"
                    try:
                        # 尝试主要演讲者选择器（带uppercase的）
                        speaker_elem = card.find_element(By.CSS_SELECTOR, "p.text-textTertiary-onLight.label1.uppercase.font-semibold")
                        speaker = speaker_elem.text.strip()
                    except:
                        try:
                            # 备用演讲者选择器（不带uppercase的）
                            speaker_elem = card.find_element(By.CSS_SELECTOR, "p.text-textTertiary-onLight.label1:not(.uppercase)")
                            speaker = speaker_elem.text.strip()
                        except:
                            pass
                    
                    # 4. 提取时长
                    duration = "未知时长"
                    try:
                        # 方法1: 使用XPath精确定位时长元素
                        duration_elem = card.find_element(By.XPATH, 
                            ".//div[contains(@class, 'absolute') and contains(@class, 'bottom-2') and contains(@class, 'right-2')]//span[contains(@class, 'font-semibold')]")
                        duration = duration_elem.text.strip()
                        
                        # 验证是否是有效的时长格式 (MM:SS)
                        if not re.match(r'\d{1,2}:\d{2}', duration):
                            duration = "未知时长"
                    except:
                        pass
                    
                    # 5. 检查是否已存在
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        videos.append(TEDVideo(
                            title=title,
                            speaker=speaker,
                            duration=duration,
                            views=0,
                            publish_date="",
                            topic="",
                            url=url
                        ))
                        logger.info(f"成功提取视频: {title} | {speaker} | {duration} | {url}")
                    else:
                        logger.debug(f"跳过已存在视频: {title}")
                        
                except Exception as e:
                    logger.warning(f"解析视频卡片失败: {e}")
                    continue
            
            logger.info(f"最终获取 {len(videos)} 个唯一视频")
            
            '''
            # debug info
            logger.info(f"提取结果: {len(videos)} 个视频")
            for i, video in enumerate(videos[:3], 1):  # 打印前3个
                logger.info(f"  {i}. 标题: {video.title}")
                logger.info(f"     演讲者: {video.speaker}")
                logger.info(f"     时长: {video.duration}")
                logger.info(f"     URL: {video.url}")
            '''

            return videos
            
        except Exception as e:
            logger.error(f"抓取视频列表失败: {e}")
            return []

    def build_talks_url_from_config(self, topics: List[str], sort: str = 'newest') -> str:
        """根据配置生成 /talks 搜索URL, 支持 topics[n] & sort & page"""
        base = f"{self.base_url}/talks"
        query: List[tuple] = []
        for idx, t in enumerate(topics):
            query.append((f"topics[{idx}]", t))
        query.append(("sort", sort))
        query.append(("language", "english"))
        query_str = urllib.parse.urlencode(query)
        return f"{base}?{query_str}"
    
    def remove_duplicates(self, videos: List[TEDVideo]) -> List[TEDVideo]:
        """根据URL去重视频列表"""
        seen = set()
        unique_videos = []
        
        for video in videos:
            # 使用URL作为唯一标识
            if video.url and video.url not in seen:
                seen.add(video.url)
                unique_videos.append(video)
        
        logger.info(f"去重前: {len(videos)} 个视频, 去重后: {len(unique_videos)} 个视频")
        return unique_videos
    
    def filter_videos_by_date(self, videos: List[TEDVideo], start_year: int = 2018, end_year: int = 2025) -> List[TEDVideo]:
        """根据发布时间筛选视频"""
        filtered_videos = []
        
        for video in videos:
            try:
                if video.publish_date:
                    date_str = video.publish_date
                    
                    if start_year <= int(date_str) <= end_year:
                        filtered_videos.append(video)
            except Exception as e:
                logger.warning(f"解析视频日期失败: {video.title} - {e}")
                continue
        
        logger.info(f"时间筛选后剩余 {len(filtered_videos)} 个视频（原{len(videos)}个）")
        return filtered_videos
    
    def filter_videos_by_duration(self, videos: List[TEDVideo], min_minutes: int = 0, max_minutes: int = 60) -> List[TEDVideo]:
        """根据时长筛选视频"""
        filtered_videos = []
        
        for video in videos:
            try:
                duration_str = video.duration.lower()
                if ':' in duration_str:
                    parts = duration_str.split(':')
                    if len(parts) == 2:
                        minutes = int(parts[0]) + int(parts[1]) / 60
                    else:
                        minutes = int(parts[0])
                elif 'min' in duration_str:
                    minutes = float(re.findall(r'\d+', duration_str)[0])
                else:
                    minutes = 0
                
                if min_minutes <= minutes <= max_minutes:
                    filtered_videos.append(video)
                    
            except Exception as e:
                logger.warning(f"解析视频时长失败: {video.title} - {e}")
                continue
        
        logger.info(f"时长筛选后剩余 {len(filtered_videos)} 个视频")
        return filtered_videos
    
    def get_video_views_and_date(self, video: TEDVideo) -> tuple:
        """获取视频播放量和发布年份"""
        if not self.driver:
            self.setup_driver()
        
        self.driver.get(video.url)
        time.sleep(2)  # 给页面基本加载留出时间
        
        # 获取页面HTML源码
        html = self.driver.page_source
        
        # 1. 提取播放量
        views = 0
        try:
            # 使用正则从HTML中直接提取播放量
            match = re.search(r'<div class="mr-1 flex items-center gap-1">([\d,]+) plays', html)
            if match:
                views_str = match.group(1).replace(',', '')
                views = int(views_str)
                logger.info(f"成功提取播放量: {views}")
            else:
                logger.warning("无法从HTML中提取播放量")
        except Exception as e:
            logger.warning(f"提取播放量失败: {e}")
        
        # 2. 提取发布年份
        publish_date = ""
        try:
            # 使用正则从HTML中直接提取年份
            match = re.search(r'<div class="text-sm text-gray-900">\s*•\s*[a-zA-Z]+\s+(\d{4})\s*</div>', html)
            if match:
                year = match.group(1)
                publish_date = year
                logger.info(f"成功提取发布年份: {year}")
            else:
                logger.warning("无法从HTML中提取发布年份")
        except Exception as e:
            logger.warning(f"提取发布年份失败: {e}")
        
        return views, publish_date


    def _iso8601_duration_to_mmss(self, iso_value: str) -> Optional[str]:
        """将 ISO 8601 PT#H#M#S 转为 mm:ss 文本"""
        try:
            match = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', iso_value or '')
            if not match:
                return None
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            total_minutes = hours * 60 + minutes
            return f"{total_minutes}:{seconds:02d}"
        except:
            return None
    
    def _parse_views(self, views_text: str) -> int:
        """解析播放量文本"""
        try:
            views_text = views_text.lower().replace('views', '').strip()
            if 'm' in views_text:
                return int(float(views_text.replace('m', '')) * 1000000)
            elif 'k' in views_text:
                return int(float(views_text.replace('k', '')) * 1000)
            else:
                return int(views_text.replace(',', ''))
        except:
            return 0

   
    
    def get_video_transcript(self, video: TEDVideo, index: int, file_head: str) -> str:
        """获取视频演讲文稿并保存到文件"""
        try:
            if not self.driver:
                self.setup_driver()
            
            logger.info(f"访问视频页面以获取演讲稿: {video.title} - {video.url}")
            self.driver.get(video.url)
            time.sleep(2)  # 给页面基本加载留出时间
            
            # 获取页面HTML源码
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找包含演讲稿的script标签
            script_tag = soup.find('script', type='application/ld+json', attrs={'data-next-head': ''})
            
            if not script_tag:
                # 尝试其他可能的script标签
                script_tags = soup.find_all('script', type='application/ld+json')
                for tag in script_tags:
                    if 'transcript' in tag.string:
                        script_tag = tag
                        break
            
            if script_tag:
                try:
                    # 解析JSON数据
                    json_data = json.loads(script_tag.string)
                    
                    # 提取演讲稿
                    transcript = json_data.get('transcript', '')
                    
                    if not transcript:
                        logger.warning("找到script标签但未找到transcript字段")
                        return ""
                    
                    # 确保transcripts目录存在
                    os.makedirs('transcripts', exist_ok=True)
                    
                    # 格式化索引为3位数
                    index_str = f"{index:03d}"
                    
                    # 生成文件名
                    filename = f"{file_head}_view_{index_str}.txt"
                    filepath = os.path.join('transcripts', filename)
                    
                    # 保存演讲稿到文件
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(transcript)
                    
                    logger.info(f"演讲稿已成功保存到 {filepath}")
                    logger.info(f"演讲稿长度: {len(transcript)} 字符")
                    
                    return transcript
                except Exception as e:
                    logger.error(f"解析JSON数据失败: {e}")
                    # 保存JSON内容用于调试
                    try:
                        with open('failed_json.json', 'w', encoding='utf-8') as f:
                            f.write(script_tag.string)
                        logger.info("失败的JSON已保存到 failed_json.json 用于调试")
                    except:
                        pass
            else:
                logger.error("未找到包含演讲稿的script标签")
                # 保存页面HTML用于调试
                with open('transcript_page.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info("页面HTML已保存到 transcript_page.html 用于调试")
            
        except Exception as e:
            logger.error(f"获取视频文稿失败: {video.title} - {e}")
        
        return ""


    
    def get_top_and_bottom_videos(self, videos: List[TEDVideo], count: int = 100) -> tuple:
        """获取播放量前N和后N的视频"""
        sorted_videos = sorted(videos, key=lambda x: x.views, reverse=True)
        
        top_videos = sorted_videos[:count]
        bottom_videos = sorted_videos[-count:] if len(sorted_videos) >= count else []
        
        return top_videos, bottom_videos
    
    def save_results(self, top_videos: List[TEDVideo], bottom_videos: List[TEDVideo], filename: str = "ted_videos_edge_results.xlsx"):
        """保存结果到Excel文件"""
        try:
            data = []
            
            for i, video in enumerate(top_videos, 1):
                data.append({
                    '排名': i,
                    '类型': '播放量前100',
                    '标题': video.title,
                    '演讲者': video.speaker,
                    '时长': video.duration,
                    '播放量': video.views,
                    '发布时间': video.publish_date,
                    #'主题': video.topic,
                    'URL': video.url
                    #'演讲文稿': video.transcript
                })
            
            for i, video in enumerate(bottom_videos, 1):
                data.append({
                    '排名': i,
                    '类型': '播放量后100',
                    '标题': video.title,
                    '演讲者': video.speaker,
                    '时长': video.duration,
                    '播放量': video.views,
                    '发布时间': video.publish_date,
                    #'主题': video.topic,
                    'URL': video.url
                    #'演讲文稿': video.transcript
                })
            
            df = pd.DataFrame(data)
            df.to_excel(filename, index=False, engine='openpyxl')
            logger.info(f"结果已保存到 {filename}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TED Edge 爬取器")
    parser.add_argument("--search-url", dest="search_url", type=str, default="", help="粘贴TED /talks 搜索URL")
    parser.add_argument("--sort", dest="sort", type=str, default=SORT, choices=["newest","oldest"], help="排序：newest 或 oldest（默认读取config）")
    args = parser.parse_args()

    scraper = TEDEdgeScraper()
    
    try:
        # 设置Edge浏览器驱动
        scraper.setup_driver()
        
        # 优先使用用户提供的 /talks 搜索URL；否则使用 config 构造
        custom_search_url = (args.search_url or '').strip()
        topics = []
        min_duration = MIN_DURATION
        max_duration = MAX_DURATION
        start_year = START_YEAR
        end_year = END_YEAR
        top_videos_count = TOP_VIDEOS_COUNT
        
        all_videos = []
        if custom_search_url:
            all_videos = scraper.get_videos_by_talks_url(custom_search_url)
        else:
            # 用 config 里的 TOPICS 生成 /talks URL 并抓取（保留 topics[n] 与 sort）
            # 注意：/talks 支持多主题组合，因此我们将 TOPICS 作为一组条件一次性抓取
            url = scraper.build_talks_url_from_config(TOPICS, sort=args.sort)
            logger.info(f"使用配置生成的URL: {url}")
            all_videos = scraper.get_videos_by_talks_url(url)
        
        logger.info(f"总共获取到 {len(all_videos)} 个视频")
        
        # 去重
        unique_videos = scraper.remove_duplicates(all_videos)
        logger.info(f"去重后共有 {len(unique_videos)} 个视频")
        
        # 根据时长筛选 当前阶段无法获取发布时间
        filtered_videos = scraper.filter_videos_by_duration(unique_videos, min_duration, max_duration)

        # 如果筛选后没有视频，使用原始去重后的视频（可能是因为日期未正确提取）
        if not filtered_videos:
            logger.warning("时长筛选后没有视频，将使用去重后的全部视频")
            filtered_videos = list(unique_videos)
        
        # 获取播放量信息
        logger.info("开始获取视频播放量 发布时间...")
        for i, video in enumerate(filtered_videos):
            logger.info(f"获取播放量 {i+1}/{len(filtered_videos)}: {video.title}")
            video.views, video.publish_date = scraper.get_video_views_and_date(video)
            time.sleep(1)
        
        # 根据日期筛选
        filtered_videos = scraper.filter_videos_by_date(filtered_videos, start_year, end_year)
        
        # 获取前100和后100的视频
        top_videos, bottom_videos = scraper.get_top_and_bottom_videos(filtered_videos, top_videos_count)
        
        # 获取前100条视频的演讲稿
        logger.info("开始获取前100条高播放量视频的演讲稿...")
        for i, video in enumerate(top_videos):
            logger.info(f"获取高播放量视频文稿 {i+1}/{len(top_videos)}: {video.title}")
            video.transcript = scraper.get_video_transcript(video, i + 1, "hight")
            time.sleep(1)

        # 获取后100条视频的演讲稿
        logger.info("开始获取后100条低播放量视频的演讲稿...")
        for i, video in enumerate(bottom_videos):
            logger.info(f"获取低播放量视频文稿 {i+1}/{len(bottom_videos)}: {video.title}")
            video.transcript = scraper.get_video_transcript(video, i + 1, "low")
            time.sleep(1)
        
        # 保存结果
        scraper.save_results(top_videos, bottom_videos)
        
        logger.info("程序执行完成！")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    main()
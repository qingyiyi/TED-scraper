#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge浏览器驱动设置辅助脚本
帮助用户解决Edge驱动问题
"""

import os
import sys
import subprocess
import requests
import zipfile
import platform
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_edge_version():
    """获取Edge浏览器版本"""
    try:
        if platform.system() == "Windows":
            # Windows系统
            import winreg
            try:
                # 尝试从注册表获取Edge版本
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\BLBeacon")
                version, _ = winreg.QueryValueEx(key, "version")
                return version
            except:
                # 如果注册表没有，尝试从程序文件获取
                edge_paths = [
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                ]
                
                for edge_path in edge_paths:
                    if os.path.exists(edge_path):
                        try:
                            process = subprocess.Popen([edge_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            output, _ = process.communicate()
                            if output:
                                version = output.decode().strip().split()[-1]
                                return version
                        except:
                            continue
        elif platform.system() == "Darwin":
            # macOS系统
            edge_paths = [
                '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
                '/Applications/Microsoft Edge Canary.app/Contents/MacOS/Microsoft Edge Canary'
            ]
            
            for edge_path in edge_paths:
                if os.path.exists(edge_path):
                    try:
                        process = subprocess.Popen([edge_path, '--version'], stdout=subprocess.PIPE)
                        output = process.communicate()[0].decode()
                        if output:
                            version = output.strip().split()[-1]
                            return version
                    except:
                        continue
        else:
            # Linux系统
            try:
                process = subprocess.Popen(['microsoft-edge', '--version'], stdout=subprocess.PIPE)
                output = process.communicate()[0].decode()
                if output:
                    version = output.strip().split()[-1]
                    return version
            except:
                pass
        
        return None
        
    except Exception as e:
        logger.warning(f"无法自动获取Edge版本: {e}")
        return None

def get_major_version(version):
    """获取主版本号"""
    if version:
        return version.split('.')[0]
    return None

def download_edgedriver(version):
    """下载Edge驱动"""
    try:
        # 创建drivers目录
        drivers_dir = "./drivers"
        if not os.path.exists(drivers_dir):
            os.makedirs(drivers_dir)
        
        # 确定下载URL和文件名
        if platform.system() == "Windows":
            url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_win64.zip"
            filename = "msedgedriver.exe"
        elif platform.system() == "Darwin":
            if platform.machine() == "arm64":
                url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_mac64_m1.zip"
            else:
                url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_mac64.zip"
            filename = "msedgedriver"
        else:
            url = f"https://msedgedriver.azureedge.net/{version}/edgedriver_linux64.zip"
            filename = "msedgedriver"
        
        zip_path = os.path.join(drivers_dir, "edgedriver.zip")
        driver_path = os.path.join(drivers_dir, filename)
        
        logger.info(f"正在下载Edge驱动版本 {version}...")
        logger.info(f"下载地址: {url}")
        
        # 下载文件
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 解压文件
        logger.info("正在解压驱动文件...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(drivers_dir)
        
        # 删除zip文件
        os.remove(zip_path)
        
        # 设置执行权限（Linux/Mac）
        if platform.system() != "Windows":
            os.chmod(driver_path, 0o755)
        
        logger.info(f"Edge驱动下载完成: {driver_path}")
        return driver_path
        
    except Exception as e:
        logger.error(f"下载Edge驱动失败: {e}")
        return None

def check_existing_driver():
    """检查是否已有Edge驱动"""
    possible_paths = [
        "./msedgedriver.exe",
        "./edgedriver.exe",
        "./drivers/msedgedriver.exe",
        "./drivers/edgedriver.exe",
        "D:/Drivers/edgedriver_win32/msedgedriver.exe"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"找到现有Edge驱动: {path}")
            return path
    
    return None

def test_driver(driver_path):
    """测试Edge驱动是否可用"""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service
        from selenium.webdriver.edge.options import Options
        
        edge_options = Options()
        edge_options.add_argument("--headless")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(driver_path)
        driver = webdriver.Edge(service=service, options=edge_options)
        driver.quit()
        
        logger.info("Edge驱动测试成功！")
        return True
        
    except Exception as e:
        logger.error(f"Edge驱动测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("        Edge浏览器驱动设置助手")
    print("=" * 60)
    
    # 检查现有驱动
    existing_driver = check_existing_driver()
    if existing_driver:
        print(f"✓ 找到现有Edge驱动: {existing_driver}")
        if test_driver(existing_driver):
            print("✓ 现有Edge驱动工作正常，无需下载")
            return
        else:
            print("✗ 现有Edge驱动无法使用，需要重新下载")
    
    # 获取Edge版本
    edge_version = get_edge_version()
    if edge_version:
        print(f"✓ 检测到Edge版本: {edge_version}")
        major_version = get_major_version(edge_version)
        print(f"✓ 主版本号: {major_version}")
    else:
        print("⚠️  无法自动检测Edge版本")
        major_version = input("请输入Edge主版本号（如：120）: ").strip()
        if not major_version:
            print("✗ 未输入版本号，退出")
            return
    
    # 下载驱动
    print(f"\n开始下载Edge驱动版本 {major_version}...")
    driver_path = download_edgedriver(major_version)
    
    if driver_path:
        print(f"✓ 下载完成: {driver_path}")
        
        # 测试驱动
        print("\n正在测试驱动...")
        if test_driver(driver_path):
            print("🎉 Edge驱动设置成功！")
            print(f"驱动路径: {driver_path}")
            print("\n现在可以运行Edge版本爬取器了！")
        else:
            print("✗ 驱动测试失败，请检查Edge版本兼容性")
    else:
        print("✗ 驱动下载失败")
        print("\n请尝试以下解决方案：")
        print("1. 检查网络连接")
        print("2. 使用VPN或代理")
        print("3. 手动下载驱动并放在项目目录")
        print("4. 使用简化版爬取器（不需要浏览器）")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        print("请检查错误信息或联系开发者")

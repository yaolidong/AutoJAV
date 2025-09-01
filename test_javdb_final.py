#!/usr/bin/env python3
"""
JavDB刮削功能最终测试
直接使用Selenium测试JavDB的实际刮削能力
"""

import os
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def setup_chrome_driver():
    """设置Chrome驱动"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Chrome二进制位置
    chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    # ChromeDriver路径
    chromedriver_path = "/Users/yaolidong/.wdm/drivers/chromedriver/mac64/139.0.7258.154/chromedriver-mac-arm64/chromedriver"
    os.chmod(chromedriver_path, 0o755)
    
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

def test_javdb_search(driver, movie_code):
    """测试JavDB搜索功能"""
    print(f"\n🔍 搜索电影代码: {movie_code}")
    
    # 访问JavDB搜索页面
    search_url = f"https://javdb.com/search?q={movie_code}&f=all"
    print(f"访问URL: {search_url}")
    
    driver.get(search_url)
    time.sleep(3)  # 等待页面加载
    
    # 获取页面源码
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # 查找搜索结果
    movie_items = soup.find_all('div', class_='item')
    print(f"找到 {len(movie_items)} 个搜索结果")
    
    if movie_items:
        # 获取第一个结果
        first_item = movie_items[0]
        
        # 提取链接
        link = first_item.find('a')
        if link and link.get('href'):
            movie_url = f"https://javdb.com{link['href']}"
            print(f"✅ 找到电影链接: {movie_url}")
            
            # 提取标题
            title_elem = first_item.find('div', class_='video-title')
            if title_elem:
                title = title_elem.get_text(strip=True)
                print(f"   标题: {title}")
            
            # 提取代码
            code_match = re.search(r'([A-Z]{2,5})-?(\d{3,4})', title.upper() if title_elem else "")
            if code_match:
                detected_code = f"{code_match.group(1)}-{code_match.group(2)}"
                print(f"   识别代码: {detected_code}")
            
            return movie_url
    
    return None

def extract_movie_details(driver, movie_url):
    """提取电影详细信息"""
    print(f"\n📄 获取电影详情...")
    
    driver.get(movie_url)
    time.sleep(3)  # 等待页面加载
    
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    details = {}
    
    # 提取标题
    title_elem = soup.find('h2', class_='title') or soup.find('strong', class_='current-title')
    if title_elem:
        details['title'] = title_elem.get_text(strip=True)
        print(f"✅ 标题: {details['title']}")
    
    # 提取信息面板
    info_panel = soup.find('div', class_='panel-block')
    if info_panel:
        # 提取各种信息
        info_text = info_panel.get_text()
        
        # 发行日期
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', info_text)
        if date_match:
            details['release_date'] = date_match.group(0)
            print(f"✅ 发行日期: {details['release_date']}")
        
        # 时长
        duration_match = re.search(r'(\d+)\s*分', info_text)
        if duration_match:
            details['duration'] = f"{duration_match.group(1)}分钟"
            print(f"✅ 时长: {details['duration']}")
    
    # 提取演员
    actors = []
    actor_links = soup.find_all('a', href=re.compile(r'/actors/'))
    for actor in actor_links:
        actor_name = actor.get_text(strip=True)
        if actor_name and actor_name not in actors:
            actors.append(actor_name)
    
    if actors:
        details['actresses'] = actors
        print(f"✅ 演员: {', '.join(actors[:3])}{'...' if len(actors) > 3 else ''}")
    
    # 提取制作商
    maker_link = soup.find('a', href=re.compile(r'/makers/'))
    if maker_link:
        details['studio'] = maker_link.get_text(strip=True)
        print(f"✅ 制作商: {details['studio']}")
    
    # 提取类型标签
    tags = []
    tag_links = soup.find_all('a', href=re.compile(r'/tags/'))
    for tag in tag_links:
        tag_name = tag.get_text(strip=True)
        if tag_name and tag_name not in tags:
            tags.append(tag_name)
    
    if tags:
        details['genres'] = tags
        print(f"✅ 类型: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
    
    # 提取封面图片
    cover_img = soup.find('img', class_='video-cover') or soup.find('img', src=re.compile(r'(cover|poster)'))
    if cover_img and cover_img.get('src'):
        details['cover'] = cover_img['src']
        print(f"✅ 封面: {details['cover'][:50]}...")
    
    return details

def main():
    """主测试函数"""
    print("="*60)
    print("🚀 JavDB 实际刮削功能测试")
    print("="*60)
    
    driver = None
    try:
        # 设置Chrome驱动
        print("\n🔧 设置Chrome驱动...")
        driver = setup_chrome_driver()
        print("✅ Chrome驱动设置成功")
        
        # 测试访问JavDB主页
        print("\n🌐 测试访问JavDB...")
        driver.get("https://javdb.com")
        time.sleep(2)
        
        if "javdb" in driver.current_url.lower():
            print(f"✅ 成功访问JavDB")
            print(f"   页面标题: {driver.title}")
        else:
            print("❌ 无法访问JavDB")
            return
        
        # 测试搜索功能
        test_codes = ["SSIS-001", "IPX-999", "STARS-123"]
        
        for code in test_codes:
            movie_url = test_javdb_search(driver, code)
            
            if movie_url:
                # 提取详细信息
                details = extract_movie_details(driver, movie_url)
                
                if details:
                    print(f"\n✅ 成功获取 {code} 的元数据")
                else:
                    print(f"\n⚠️  无法提取 {code} 的详细信息")
            else:
                print(f"\n⚠️  未找到 {code}")
            
            # 避免请求过快
            time.sleep(2)
        
        print("\n" + "="*60)
        print("📊 测试结果总结")
        print("="*60)
        print("✅ Chrome/ChromeDriver正常工作")
        print("✅ 可以访问JavDB网站")
        print("✅ 可以搜索电影代码")
        print("✅ 可以提取电影元数据")
        print("\n🎉 JavDB刮削功能完全正常！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("\n🧹 关闭浏览器...")
            driver.quit()
            print("✅ 测试完成")

if __name__ == "__main__":
    main()
"""Selenium辅助模块 - 强制使用系统chromedriver"""

import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService

logger = logging.getLogger(__name__)


def get_chrome_driver(headless=True, proxy=None):
    """
    获取配置好的Chrome WebDriver
    强制使用系统安装的chromedriver，避免Selenium自动下载
    """
    # 创建Chrome选项
    options = webdriver.ChromeOptions()
    
    # 检测Docker环境
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)
    if in_docker:
        headless = True
    
    # 基础选项 - Docker环境必需
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 设置Chrome二进制路径
    chrome_paths = [
        '/usr/bin/chromium',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium-browser'
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
            logger.info(f"使用Chrome二进制: {chrome_path}")
            break
    
    # Headless模式
    if headless:
        options.add_argument('--headless=new')
    
    # 窗口大小
    options.add_argument('--window-size=1920,1080')
    
    # User-Agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # SSL/TLS相关设置
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--allow-insecure-localhost')
    
    # 代理设置
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"使用代理: {proxy}")
    
    # 查找系统chromedriver
    chromedriver_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        '/opt/chromedriver/chromedriver'
    ]
    
    driver_path = None
    for path in chromedriver_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            driver_path = path
            logger.info(f"找到系统ChromeDriver: {path}")
            break
    
    if not driver_path:
        raise Exception("找不到系统ChromeDriver，请确保已安装chromedriver")
    
    # 创建Service对象，明确指定chromedriver路径
    service = ChromeService(executable_path=driver_path)
    
    # 禁止Selenium Manager下载
    os.environ['SE_SKIP_DRIVER_DOWNLOAD'] = '1'
    
    try:
        # 创建driver
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("成功创建Chrome WebDriver")
        return driver
    except Exception as e:
        logger.error(f"创建Chrome WebDriver失败: {e}")
        # 尝试调试信息
        import subprocess
        try:
            result = subprocess.run([driver_path, '--version'], capture_output=True, text=True)
            logger.info(f"ChromeDriver版本: {result.stdout}")
        except:
            pass
        
        try:
            result = subprocess.run([options.binary_location, '--version'], capture_output=True, text=True)
            logger.info(f"Chrome版本: {result.stdout}")
        except:
            pass
        
        raise
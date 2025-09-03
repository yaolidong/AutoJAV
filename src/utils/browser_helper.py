"""浏览器辅助工具 - 处理Docker环境中的浏览器启动"""

import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)


def create_chrome_driver(headless: bool = True, proxy: str = None, user_data_dir: str = None) -> webdriver.Chrome:
    """
    创建Chrome WebDriver实例，自动处理Docker环境
    
    Args:
        headless: 是否使用无头模式
        proxy: 代理服务器地址
        user_data_dir: 持久化用户配置目录
    
    Returns:
        配置好的Chrome WebDriver实例
    """
    options = Options()
    
    # 检测是否在Docker环境中
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)
    
    # Docker环境强制使用headless
    if in_docker:
        headless = True
        logger.info("检测到Docker环境，强制使用headless模式")
    
    # 设置Chrome二进制文件路径
    chrome_binary = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
    if os.path.exists(chrome_binary):
        options.binary_location = chrome_binary
        logger.info(f"使用Chrome二进制文件: {chrome_binary}")
    
    # 基本选项
    if headless:
        options.add_argument('--headless=new')  # 使用新的headless模式
        options.add_argument('--disable-gpu')
    
    # Docker必需选项
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    # 性能优化选项
    options.add_argument('--memory-pressure-off')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    
    # 设置窗口大小
    options.add_argument('--window-size=1920,1080')
    
    # 设置User-Agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 用户配置目录
    if user_data_dir:
        options.add_argument(f'--user-data-dir={user_data_dir}')
        logger.info(f"使用持久化用户配置目录: {user_data_dir}")
    
    # 代理设置
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"使用代理: {proxy}")
    
    # 创建WebDriver
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
    
    if not os.path.exists(chromedriver_path):
        # 尝试其他路径
        alternative_paths = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/opt/chromedriver/chromedriver'
        ]
        for path in alternative_paths:
            if os.path.exists(path):
                chromedriver_path = path
                break
    
    logger.info(f"使用ChromeDriver: {chromedriver_path}")
    
    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("成功创建Chrome WebDriver")
        return driver
    except Exception as e:
        logger.error(f"创建Chrome WebDriver失败: {str(e)}")
        
        # 尝试不指定chromedriver路径，让Selenium自动查找
        try:
            logger.info("尝试让Selenium自动查找ChromeDriver...")
            driver = webdriver.Chrome(options=options)
            logger.info("成功使用自动检测的ChromeDriver")
            return driver
        except Exception as e2:
            logger.error(f"自动查找ChromeDriver也失败: {str(e2)}")
            raise


def test_chrome_driver():
    """测试Chrome WebDriver是否能正常工作"""
    try:
        driver = create_chrome_driver(headless=True)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        logger.info(f"Chrome WebDriver测试成功，页面标题: {title}")
        return True
    except Exception as e:
        logger.error(f"Chrome WebDriver测试失败: {str(e)}")
        return False
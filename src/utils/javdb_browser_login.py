"""JavDB浏览器登录模块 - 打开真实浏览器窗口让用户登录"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional
import threading
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 尝试导入browser_helper，如果失败则使用内置方法
try:
    from .browser_helper import create_chrome_driver
except ImportError:
    create_chrome_driver = None

logger = logging.getLogger(__name__)


class JavDBBrowserLogin:
    """JavDB浏览器登录管理器 - 打开真实浏览器窗口"""
    
    def __init__(self, config_dir: str = "/app/config", headless: bool = False):
        """
        初始化登录管理器
        
        Args:
            config_dir: 配置目录路径
            headless: 是否使用无头模式（False则显示浏览器窗口）
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = self.config_dir / "javdb_cookies.json"
        self.driver = None
        # 在Docker环境中强制使用headless模式
        import os
        self.in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)
        self.headless = headless or self.in_docker
        self.login_success = False
        self.monitor_thread = None
        self.stop_monitor = False
        
    def open_login_window(self) -> Dict[str, any]:
        """
        打开JavDB登录窗口，等待用户登录
        
        Returns:
            包含登录结果的字典
        """
        try:
            # 获取代理配置
            proxy = self._get_proxy_config()
            
            # 尝试使用selenium_helper
            try:
                from .selenium_helper import get_chrome_driver
                logger.info("使用selenium_helper创建Chrome驱动...")
                self.driver = get_chrome_driver(headless=self.headless, proxy=proxy)
                logger.info("成功创建Chrome驱动")
            except ImportError:
                logger.warning("selenium_helper不可用，使用备用方法")
                self.driver = None
            except Exception as e:
                logger.error(f"selenium_helper创建驱动失败: {e}")
                self.driver = None
            
            # 如果browser_helper失败或不可用，使用备用方法
            if not self.driver:
                logger.info("使用备用方法创建Chrome驱动...")
                from selenium.webdriver.chrome.service import Service
                import os
                
                options = webdriver.ChromeOptions()
                
                # 强制headless模式在Docker环境
                if self.in_docker:
                    self.headless = True
                    logger.info("Docker环境检测，强制使用headless模式")
                
                # 设置Chrome二进制路径
                chrome_binary = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
                if os.path.exists(chrome_binary):
                    options.binary_location = chrome_binary
                    logger.info(f"使用Chrome二进制: {chrome_binary}")
                
                # 基本选项
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-setuid-sandbox')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                if self.headless:
                    options.add_argument('--headless=new')
                
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                if proxy:
                    options.add_argument(f'--proxy-server={proxy}')
                    logger.info(f"使用代理: {proxy}")
                
                # 使用系统chromedriver
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
                
                # 检查多个可能的路径
                possible_paths = [
                    chromedriver_path,
                    '/usr/bin/chromedriver',
                    '/usr/local/bin/chromedriver'
                ]
                
                driver_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        driver_path = path
                        logger.info(f"找到ChromeDriver: {path}")
                        break
                
                try:
                    if driver_path:
                        # 使用系统的chromedriver
                        service = Service(executable_path=driver_path)
                        self.driver = webdriver.Chrome(service=service, options=options)
                        logger.info(f"成功使用系统ChromeDriver: {driver_path}")
                    else:
                        # 如果找不到系统chromedriver，尝试默认方式
                        self.driver = webdriver.Chrome(options=options)
                        logger.info("成功使用Selenium默认方式创建Chrome驱动")
                except Exception as e:
                    logger.error(f"创建Chrome驱动失败: {str(e)}")
                    return {
                        'success': False,
                        'error': f'无法启动浏览器: {str(e)}. 请确保Chrome/Chromium已正确安装。'
                    }
            self.driver.set_page_load_timeout(30)
            
            # 访问JavDB登录页面
            logger.info("访问JavDB登录页面...")
            self.driver.get("https://javdb.com/login")
            
            # 启动监控线程，检测登录状态
            self.stop_monitor = False
            self.monitor_thread = threading.Thread(target=self._monitor_login_status)
            self.monitor_thread.start()
            
            return {
                'success': True,
                'message': '浏览器窗口已打开，请在浏览器中完成登录',
                'window_open': True
            }
            
        except WebDriverException as e:
            logger.error(f"无法启动浏览器: {e}")
            return {
                'success': False,
                'error': '无法启动浏览器，请确保Chrome和ChromeDriver已安装'
            }
        except Exception as e:
            logger.error(f"打开登录窗口失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_proxy_config(self) -> Optional[str]:
        """获取代理配置"""
        try:
            config_file = self.config_dir / "config.yaml"
            if config_file.exists():
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    proxy_url = config.get('network', {}).get('proxy_url')
                    if proxy_url:
                        # 处理不同的代理格式
                        if proxy_url.startswith('socks'):
                            return f'socks5://{proxy_url.split("://")[1]}'
                        return proxy_url
        except Exception as e:
            logger.warning(f"读取代理配置失败: {e}")
        return None
    
    def _monitor_login_status(self):
        """监控登录状态的线程函数"""
        logger.info("开始监控登录状态...")
        max_wait_time = 300  # 最多等待5分钟
        start_time = time.time()
        
        while not self.stop_monitor and (time.time() - start_time) < max_wait_time:
            try:
                if self.driver:
                    current_url = self.driver.current_url
                    
                    # 检查是否已经登录成功（URL不再是login页面）
                    if "login" not in current_url.lower():
                        # 等待页面完全加载
                        time.sleep(2)
                        
                        # 检查是否有用户信息元素（表示已登录）
                        try:
                            # 尝试查找用户菜单或其他登录后才有的元素
                            user_element = self.driver.find_element(By.CSS_SELECTOR, 
                                ".navbar-user, .user-menu, .avatar, [href*='users'], [href*='logout']")
                            
                            if user_element:
                                logger.info("检测到用户已登录")
                                self.login_success = True
                                self._save_cookies()
                                break
                        except:
                            pass
                    
                    # 检查是否有登录成功的提示
                    try:
                        success_element = self.driver.find_element(By.CSS_SELECTOR, 
                            ".alert-success, .toast-success, .notification-success")
                        if success_element:
                            logger.info("检测到登录成功提示")
                            time.sleep(2)
                            self.login_success = True
                            self._save_cookies()
                            break
                    except:
                        pass
                
            except Exception as e:
                logger.debug(f"监控登录状态时出错: {e}")
            
            time.sleep(1)  # 每秒检查一次
        
        if self.login_success:
            logger.info("登录成功，正在关闭浏览器...")
            self._close_browser()
        elif time.time() - start_time >= max_wait_time:
            logger.warning("登录超时")
            self._close_browser()
    
    def _save_cookies(self):
        """保存cookies到文件"""
        try:
            if self.driver:
                cookies = self.driver.get_cookies()
                
                # 保存cookies
                cookies_data = {
                    'cookies': cookies,
                    'timestamp': time.time(),
                    'source': 'browser_login',
                    'url': self.driver.current_url
                }
                
                with open(self.cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Cookies已保存到 {self.cookies_file}")
                logger.info(f"保存了 {len(cookies)} 个cookies")
                return True
                
        except Exception as e:
            logger.error(f"保存cookies失败: {e}")
            return False
    
    def _close_browser(self):
        """关闭浏览器"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {e}")
    
    def check_login_status(self) -> Dict[str, any]:
        """检查登录状态"""
        return {
            'success': True,
            'logged_in': self.login_success,
            'window_open': self.driver is not None
        }
    
    def close_window(self) -> Dict[str, any]:
        """手动关闭登录窗口"""
        self.stop_monitor = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        self._close_browser()
        
        return {
            'success': True,
            'message': '登录窗口已关闭',
            'logged_in': self.login_success
        }
    
    def cleanup(self):
        """清理资源"""
        self.stop_monitor = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        self._close_browser()
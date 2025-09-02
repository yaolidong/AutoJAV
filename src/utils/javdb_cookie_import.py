#!/usr/bin/env python3
"""
JavDB Cookie Import Tool - 导入和验证cookies
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JavDBCookieImporter:
    """处理JavDB cookies的导入和验证"""
    
    def __init__(self, config_dir: str = "/app/config"):
        self.config_dir = Path(config_dir)
        self.cookie_file = self.config_dir / "javdb_cookies.json"
        self.base_url = "https://javdb.com"
        
    def import_cookies_from_browser(self, browser_cookies: List[Dict]) -> bool:
        """
        从浏览器导出的cookies导入
        
        Args:
            browser_cookies: 浏览器导出的cookie列表
        """
        try:
            # 确保必要的cookie字段存在
            processed_cookies = []
            for cookie in browser_cookies:
                # 处理cookie格式
                processed_cookie = {
                    "name": cookie.get("name"),
                    "value": cookie.get("value"),
                    "domain": cookie.get("domain", ".javdb.com"),
                    "path": cookie.get("path", "/"),
                    "secure": cookie.get("secure", False),
                    "httpOnly": cookie.get("httpOnly", False)
                }
                
                # 处理expiry字段
                if "expiry" in cookie:
                    processed_cookie["expiry"] = cookie["expiry"]
                elif "expirationDate" in cookie:
                    processed_cookie["expiry"] = int(cookie["expirationDate"])
                    
                # 处理sameSite字段
                if "sameSite" in cookie:
                    processed_cookie["sameSite"] = cookie["sameSite"]
                else:
                    processed_cookie["sameSite"] = "Lax"
                    
                processed_cookies.append(processed_cookie)
            
            # 保存cookies
            cookie_data = {
                "cookies": processed_cookies,
                "timestamp": datetime.now().isoformat(),
                "domain": self.base_url
            }
            
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            logger.info(f"成功导入 {len(processed_cookies)} 个cookies")
            return True
            
        except Exception as e:
            logger.error(f"导入cookies失败: {e}")
            return False
    
    def verify_cookies_enhanced(self) -> Dict:
        """
        增强的cookie验证，返回详细的验证结果
        """
        result = {
            "valid": False,
            "logged_in": False,
            "error": None,
            "details": {}
        }
        
        driver = None
        try:
            # 读取cookies
            if not self.cookie_file.exists():
                result["error"] = "Cookie文件不存在"
                return result
                
            with open(self.cookie_file, 'r') as f:
                cookie_data = json.load(f)
            
            cookies = cookie_data.get("cookies", [])
            if not cookies:
                result["error"] = "没有找到cookies"
                return result
            
            # 设置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            logger.info("启动Chrome进行cookie验证...")
            driver = webdriver.Chrome(options=chrome_options)
            
            # 首先访问主页（重要：必须先访问网站才能设置cookies）
            logger.info(f"访问 {self.base_url}")
            driver.get(self.base_url)
            time.sleep(1)
            
            # 添加cookies
            cookies_added = 0
            cookies_failed = 0
            
            for cookie in cookies:
                try:
                    # 清理cookie数据
                    clean_cookie = {}
                    
                    # 必要字段
                    clean_cookie["name"] = cookie.get("name")
                    clean_cookie["value"] = cookie.get("value")
                    
                    # 可选字段
                    if "domain" in cookie:
                        # 确保domain匹配当前网站
                        domain = cookie["domain"]
                        if domain.startswith("."):
                            clean_cookie["domain"] = domain
                        else:
                            clean_cookie["domain"] = "." + domain if not domain.startswith("javdb.com") else domain
                    
                    if "path" in cookie:
                        clean_cookie["path"] = cookie["path"]
                    
                    if "secure" in cookie:
                        clean_cookie["secure"] = cookie["secure"]
                    
                    if "httpOnly" in cookie:
                        clean_cookie["httpOnly"] = cookie["httpOnly"]
                    
                    if "expiry" in cookie and cookie["expiry"]:
                        # 确保expiry是整数
                        clean_cookie["expiry"] = int(cookie["expiry"])
                    
                    # sameSite处理
                    if "sameSite" in cookie:
                        # Selenium可能不支持'None'值
                        if cookie["sameSite"] == "None":
                            clean_cookie["sameSite"] = "Lax"
                        else:
                            clean_cookie["sameSite"] = cookie["sameSite"]
                    
                    driver.add_cookie(clean_cookie)
                    cookies_added += 1
                    logger.debug(f"添加cookie成功: {clean_cookie['name']}")
                    
                except Exception as e:
                    cookies_failed += 1
                    logger.debug(f"添加cookie失败: {cookie.get('name', 'unknown')} - {e}")
            
            result["details"]["cookies_added"] = cookies_added
            result["details"]["cookies_failed"] = cookies_failed
            
            # 刷新页面以应用cookies
            logger.info("刷新页面以应用cookies...")
            driver.refresh()
            time.sleep(3)
            
            # 检查登录状态 - 多种方式验证
            logger.info("检查登录状态...")
            
            # 方法1：查找登出链接
            logout_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/logout')]")
            if logout_links:
                result["logged_in"] = True
                result["details"]["logout_link_found"] = True
                logger.info("找到登出链接 - 已登录")
            
            # 方法2：查找用户菜单或头像
            user_elements = driver.find_elements(By.CSS_SELECTOR, ".user-menu, .avatar, .user-info, [class*='user']")
            if user_elements:
                result["logged_in"] = True
                result["details"]["user_menu_found"] = True
                logger.info("找到用户菜单 - 已登录")
            
            # 方法3：检查页面是否重定向到登录页
            current_url = driver.current_url
            if "/login" in current_url:
                result["logged_in"] = False
                result["details"]["redirected_to_login"] = True
                logger.info("被重定向到登录页 - 未登录")
            else:
                result["details"]["current_url"] = current_url
            
            # 方法4：尝试访问需要登录的页面
            if not result["logged_in"]:
                logger.info("尝试访问用户页面...")
                driver.get(f"{self.base_url}/users")
                time.sleep(2)
                
                if "/login" not in driver.current_url:
                    result["logged_in"] = True
                    result["details"]["user_page_accessible"] = True
                    logger.info("可以访问用户页面 - 已登录")
            
            # 设置最终结果
            result["valid"] = result["logged_in"]
            
            if result["valid"]:
                result["error"] = None
                logger.info("Cookie验证成功 - 已登录")
            else:
                result["error"] = "Cookies无效或已过期"
                logger.warning("Cookie验证失败 - 未登录")
            
            return result
            
        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            result["error"] = str(e)
            return result
            
        finally:
            if driver:
                driver.quit()
    
    def fix_cookie_format(self) -> bool:
        """
        修复cookie文件格式问题
        """
        try:
            if not self.cookie_file.exists():
                logger.error("Cookie文件不存在")
                return False
            
            # 读取现有cookies
            with open(self.cookie_file, 'r') as f:
                data = json.load(f)
            
            # 如果直接是cookie数组，转换为标准格式
            if isinstance(data, list):
                cookies = data
                data = {
                    "cookies": cookies,
                    "timestamp": datetime.now().isoformat(),
                    "domain": self.base_url
                }
            
            # 修复每个cookie
            fixed_cookies = []
            for cookie in data.get("cookies", []):
                # 确保必要字段存在
                if not cookie.get("name") or not cookie.get("value"):
                    continue
                
                # 修复domain
                if not cookie.get("domain"):
                    cookie["domain"] = ".javdb.com"
                elif not cookie["domain"].startswith(".") and "javdb.com" in cookie["domain"]:
                    cookie["domain"] = "." + cookie["domain"]
                
                # 修复path
                if not cookie.get("path"):
                    cookie["path"] = "/"
                
                # 修复sameSite
                if cookie.get("sameSite") == "None":
                    cookie["sameSite"] = "Lax"
                elif not cookie.get("sameSite"):
                    cookie["sameSite"] = "Lax"
                
                fixed_cookies.append(cookie)
            
            # 保存修复后的cookies
            data["cookies"] = fixed_cookies
            data["timestamp"] = datetime.now().isoformat()
            
            with open(self.cookie_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"修复了 {len(fixed_cookies)} 个cookies")
            return True
            
        except Exception as e:
            logger.error(f"修复cookie格式失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JavDB Cookie导入和验证工具')
    parser.add_argument('--import', dest='import_file', help='导入cookie文件')
    parser.add_argument('--verify', action='store_true', help='验证cookies')
    parser.add_argument('--fix', action='store_true', help='修复cookie格式')
    parser.add_argument('--config-dir', default='/app/config', help='配置目录')
    
    args = parser.parse_args()
    
    importer = JavDBCookieImporter(config_dir=args.config_dir)
    
    if args.import_file:
        # 导入cookies
        with open(args.import_file, 'r') as f:
            cookies = json.load(f)
            if isinstance(cookies, dict):
                cookies = cookies.get("cookies", cookies)
            success = importer.import_cookies_from_browser(cookies)
            if success:
                print("✅ Cookies导入成功")
            else:
                print("❌ Cookies导入失败")
    
    if args.fix:
        # 修复格式
        success = importer.fix_cookie_format()
        if success:
            print("✅ Cookie格式修复成功")
        else:
            print("❌ Cookie格式修复失败")
    
    if args.verify or args.import_file or args.fix:
        # 验证cookies
        result = importer.verify_cookies_enhanced()
        print("\n验证结果:")
        print("-" * 40)
        print(f"有效: {result['valid']}")
        print(f"已登录: {result['logged_in']}")
        if result['error']:
            print(f"错误: {result['error']}")
        if result['details']:
            print(f"详情: {json.dumps(result['details'], indent=2)}")


if __name__ == "__main__":
    main()
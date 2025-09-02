#!/usr/bin/env python3
"""
JavDB Manual Login with VNC/Remote debugging support
Provides multiple methods for manual login to JavDB
"""

import json
import time
import logging
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

class JavDBLoginVNC:
    """Enhanced JavDB login manager with multiple login methods"""
    
    def __init__(self, config_dir: str = "/app/config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.config_dir / "javdb_cookies.json"
        self.base_url = "https://javdb.com"
        self.login_url = "https://javdb.com/login"
        
    def generate_login_url(self, return_url: str = None) -> Dict:
        """
        Generate a login URL with token for authentication outside container
        """
        import uuid
        import hashlib
        
        # Generate a unique token
        token = str(uuid.uuid4())
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Save token temporarily
        token_file = self.config_dir / f"login_token_{token_hash}.json"
        token_data = {
            "token": token,
            "created": datetime.now().isoformat(),
            "return_url": return_url or "http://localhost:8080",
            "status": "pending"
        }
        
        with open(token_file, 'w') as f:
            json.dump(token_data, f)
        
        # Create login helper HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>JavDB Login Helper</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .step {{
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #007bff;
        }}
        .step h3 {{
            margin-top: 0;
            color: #007bff;
        }}
        button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }}
        button:hover {{
            background: #0056b3;
        }}
        .success {{
            background: #d4edda;
            border-color: #28a745;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }}
        .error {{
            background: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }}
        #status {{
            margin-top: 20px;
            padding: 15px;
            background: #e9ecef;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 JavDB 登录助手</h1>
        
        <div class="step">
            <h3>步骤 1: 登录JavDB</h3>
            <p>点击下面的按钮在新窗口中打开JavDB登录页面：</p>
            <button onclick="window.open('{self.login_url}', '_blank')">打开JavDB登录页面</button>
        </div>
        
        <div class="step">
            <h3>步骤 2: 完成登录</h3>
            <p>在新打开的JavDB页面中输入您的账号密码并完成登录。</p>
        </div>
        
        <div class="step">
            <h3>步骤 3: 获取Cookies</h3>
            <p>登录成功后，点击下面的按钮获取并保存Cookies：</p>
            <button onclick="getCookies()">获取并保存Cookies</button>
        </div>
        
        <div id="status"></div>
    </div>
    
    <script>
        function getCookies() {{
            document.getElementById('status').innerHTML = '<p>⏳ 正在获取Cookies...</p>';
            
            // 提示用户如何手动获取cookies
            const instructions = `
                <div class="step">
                    <h3>手动获取Cookies方法：</h3>
                    <ol>
                        <li>确保您已经在JavDB网站上登录成功</li>
                        <li>在JavDB页面上按 F12 打开开发者工具</li>
                        <li>切换到 "Application" 或 "存储" 标签</li>
                        <li>在左侧找到 "Cookies" -> "https://javdb.com"</li>
                        <li>复制所有cookie信息</li>
                        <li>将cookie信息保存到配置目录</li>
                    </ol>
                </div>
                <div class="success">
                    <p>✅ 请按照上述步骤手动获取Cookies</p>
                    <p>Token: {token}</p>
                    <p>完成后，您可以关闭此页面</p>
                </div>
            `;
            document.getElementById('status').innerHTML = instructions;
        }}
    </script>
</body>
</html>
"""
        
        # Save HTML file
        html_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False)
        html_file.write(html_content)
        html_file.flush()
        
        return {
            "success": True,
            "token": token,
            "token_hash": token_hash,
            "html_file": html_file.name,
            "login_url": self.login_url,
            "instructions": "Open the HTML file in your browser to complete login"
        }
    
    def login_with_remote_debugging(self, debugging_port: int = 9222) -> bool:
        """
        使用Chrome远程调试模式登录
        用户需要在主机上打开Chrome并启用远程调试
        """
        try:
            logger.info(f"尝试连接到Chrome远程调试端口 {debugging_port}")
            
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debugging_port}")
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # 导航到JavDB登录页
            driver.get(self.login_url)
            
            print("\n" + "="*60)
            print("请在Chrome浏览器中完成JavDB登录")
            print("登录成功后，按Enter键继续...")
            print("="*60)
            
            input()  # 等待用户完成登录
            
            # 获取并保存cookies
            cookies = driver.get_cookies()
            if self.save_cookies(cookies):
                logger.info("Cookies保存成功")
                return True
            else:
                logger.error("Cookies保存失败")
                return False
                
        except Exception as e:
            logger.error(f"远程调试连接失败: {e}")
            print("\n请确保在主机上运行Chrome并启用远程调试：")
            print("chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
            return False
    
    def login_headless_with_credentials(self, username: str, password: str) -> bool:
        """
        使用提供的凭据在headless模式下登录
        注意：这种方法可能会被反爬虫机制阻止
        """
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # 访问登录页面
            driver.get(self.login_url)
            time.sleep(2)
            
            # 查找并填写登录表单
            # 注意：这些选择器可能需要根据实际页面调整
            try:
                username_field = driver.find_element(By.NAME, "username")
                password_field = driver.find_element(By.NAME, "password")
                
                username_field.send_keys(username)
                password_field.send_keys(password)
                
                # 提交表单
                login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
                
                # 等待登录完成
                time.sleep(5)
                
                # 检查是否登录成功
                if self.check_login_status(driver):
                    cookies = driver.get_cookies()
                    if self.save_cookies(cookies):
                        logger.info("自动登录成功，Cookies已保存")
                        return True
            except Exception as e:
                logger.error(f"自动登录失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Headless登录错误: {e}")
            return False
        finally:
            if driver:
                driver.quit()
    
    def save_cookies(self, cookies: List[Dict]) -> bool:
        """保存cookies到文件"""
        try:
            cookie_data = {
                "cookies": cookies,
                "timestamp": datetime.now().isoformat(),
                "domain": self.base_url
            }
            
            with open(self.cookie_file, 'w') as f:
                json.dump(cookie_data, f, indent=2)
            
            self.cookie_file.chmod(0o600)
            return True
            
        except Exception as e:
            logger.error(f"保存cookies失败: {e}")
            return False
    
    def check_login_status(self, driver) -> bool:
        """检查是否登录成功"""
        try:
            # 查找登出链接或用户菜单
            logout_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/logout')]")
            user_elements = driver.find_elements(By.CSS_SELECTOR, ".user-menu, .avatar")
            return len(logout_elements) > 0 or len(user_elements) > 0
        except:
            return False
    
    def get_cookie_status(self) -> Dict:
        """获取cookie状态"""
        if not self.cookie_file.exists():
            return {
                "exists": False,
                "valid": False,
                "message": "No cookies saved"
            }
        
        try:
            with open(self.cookie_file, 'r') as f:
                cookie_data = json.load(f)
            
            timestamp = datetime.fromisoformat(cookie_data.get("timestamp", ""))
            age_days = (datetime.now() - timestamp).days
            
            return {
                "exists": True,
                "timestamp": cookie_data.get("timestamp"),
                "age_days": age_days,
                "cookie_count": len(cookie_data.get("cookies", [])),
                "valid": age_days < 30,
                "message": f"Cookies saved {age_days} days ago"
            }
        except Exception as e:
            return {
                "exists": True,
                "valid": False,
                "error": str(e),
                "message": "Error reading cookies"
            }


def main():
    """主函数，提供多种登录方式"""
    import argparse
    import sys
    from src.utils.logging_config import setup_application_logging
    
    setup_application_logging()
    
    parser = argparse.ArgumentParser(description='JavDB Enhanced Login Manager')
    parser.add_argument('--method', choices=['url', 'remote', 'headless', 'status'], 
                       default='url', help='Login method to use')
    parser.add_argument('--port', type=int, default=9222, 
                       help='Chrome remote debugging port')
    parser.add_argument('--username', help='Username for headless login')
    parser.add_argument('--password', help='Password for headless login')
    parser.add_argument('--config-dir', default='/app/config', 
                       help='Config directory path')
    
    args = parser.parse_args()
    
    manager = JavDBLoginVNC(config_dir=args.config_dir)
    
    if args.method == 'status':
        status = manager.get_cookie_status()
        print("\nCookie Status:")
        print("-" * 40)
        for key, value in status.items():
            print(f"{key}: {value}")
        sys.exit(0)
    
    elif args.method == 'url':
        print("\n使用URL方式登录...")
        result = manager.generate_login_url()
        if result['success']:
            print("\n" + "="*60)
            print("登录准备完成！")
            print("="*60)
            print(f"\n1. 在浏览器中打开: file://{result['html_file']}")
            print("2. 按照页面指示完成登录")
            print(f"3. Token: {result['token']}")
            print("\n提示：您也可以直接访问 {result['login_url']} 手动登录")
            
            # 尝试自动打开浏览器
            try:
                webbrowser.open(f"file://{result['html_file']}")
                print("\n浏览器已自动打开，请完成登录操作")
            except:
                print("\n无法自动打开浏览器，请手动打开上述URL")
    
    elif args.method == 'remote':
        print("\n使用Chrome远程调试方式...")
        print("\n请先在主机上启动Chrome并启用远程调试：")
        print(f"chrome --remote-debugging-port={args.port} --user-data-dir=/tmp/chrome-debug")
        print("\n按Enter键继续...")
        input()
        
        success = manager.login_with_remote_debugging(args.port)
        sys.exit(0 if success else 1)
    
    elif args.method == 'headless':
        if not args.username or not args.password:
            print("错误：Headless登录需要提供用户名和密码")
            print("使用: --username YOUR_USERNAME --password YOUR_PASSWORD")
            sys.exit(1)
        
        print("\n使用Headless方式自动登录...")
        success = manager.login_headless_with_credentials(args.username, args.password)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
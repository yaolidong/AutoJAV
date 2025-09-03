"""JavDB模拟登录模块 - 用于测试和演示"""

import json
import logging
import time
import base64
from pathlib import Path
from typing import Dict, Optional
import threading

logger = logging.getLogger(__name__)


class JavDBMockLogin:
    """JavDB模拟登录管理器 - 用于测试和演示功能"""
    
    def __init__(self, config_dir: str = "/app/config"):
        """
        初始化模拟登录管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = self.config_dir / "javdb_cookies.json"
        self.login_success = False
        self.current_page = "login"
        self.screenshot_html = ""
        
    def start_browser(self) -> Dict[str, any]:
        """
        模拟启动浏览器
        
        Returns:
            包含状态的字典
        """
        try:
            logger.info("启动模拟浏览器...")
            
            # 生成登录页面HTML
            self.screenshot_html = """
            <html>
            <head>
                <title>JavDB Login</title>
                <style>
                    body { font-family: Arial; padding: 20px; background: #f0f0f0; }
                    .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    h1 { color: #333; text-align: center; }
                    .warning { background: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
                    input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                    button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                    button:hover { background: #0056b3; }
                    .info { color: #666; font-size: 14px; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>JavDB 登录</h1>
                    <div class="warning">
                        ⚠️ 测试模式：由于网络限制，当前为模拟界面。<br>
                        实际使用时需要配置代理或VPN。
                    </div>
                    <form id="loginForm">
                        <input type="text" id="username" placeholder="用户名" value="">
                        <input type="password" id="password" placeholder="密码" value="">
                        <button type="submit">登录</button>
                    </form>
                    <div class="info">
                        提示：这是一个模拟界面，用于演示登录流程。<br>
                        输入任意用户名和密码，点击登录按钮即可模拟成功。
                    </div>
                </div>
            </body>
            </html>
            """
            
            self.current_page = "login"
            
            return {
                'success': True,
                'message': '模拟浏览器已启动，显示登录页面'
            }
            
        except Exception as e:
            logger.error(f"启动模拟浏览器失败: {e}")
            return {
                'success': False,
                'error': f'无法启动模拟浏览器: {str(e)}'
            }
    
    def get_screenshot(self) -> Dict[str, any]:
        """
        获取当前页面截图（返回HTML）
        
        Returns:
            包含截图的字典
        """
        try:
            # 将HTML转换为base64编码的图片数据URL
            # 这里使用HTML内容作为"截图"
            html_bytes = self.screenshot_html.encode('utf-8')
            screenshot_data = base64.b64encode(html_bytes).decode('utf-8')
            
            return {
                'success': True,
                'screenshot': screenshot_data,
                'current_url': f'mock://javdb.com/{self.current_page}',
                'is_logged_in': self.login_success,
                'is_html': True  # 标记这是HTML内容而不是图片
            }
            
        except Exception as e:
            logger.error(f"获取截图失败: {e}")
            return {
                'success': False,
                'error': f'无法获取截图: {str(e)}'
            }
    
    def send_input(self, selector: str, text: str) -> Dict[str, any]:
        """
        模拟发送输入
        
        Args:
            selector: 元素选择器
            text: 输入的文本
            
        Returns:
            操作结果
        """
        try:
            logger.info(f"模拟输入到 {selector}: {text[:20]}...")
            
            # 更新HTML以显示输入的内容
            if 'username' in selector:
                self.screenshot_html = self.screenshot_html.replace('value=""', f'value="{text}"', 1)
            elif 'password' in selector:
                # 密码用星号显示
                masked = '*' * len(text)
                self.screenshot_html = self.screenshot_html.replace('value=""', f'value="{masked}"', 1)
            
            return {
                'success': True,
                'message': f'已输入到 {selector}'
            }
            
        except Exception as e:
            logger.error(f"输入失败: {e}")
            return {
                'success': False,
                'error': f'输入失败: {str(e)}'
            }
    
    def click_element(self, selector: str) -> Dict[str, any]:
        """
        模拟点击元素
        
        Args:
            selector: 元素选择器
            
        Returns:
            操作结果
        """
        try:
            logger.info(f"模拟点击 {selector}")
            
            # 如果点击登录按钮，模拟登录成功
            if 'submit' in selector or 'login' in selector.lower():
                self.login_success = True
                self.current_page = "home"
                
                # 生成登录成功页面
                self.screenshot_html = """
                <html>
                <head>
                    <title>JavDB - 已登录</title>
                    <style>
                        body { font-family: Arial; padding: 20px; background: #f0f0f0; }
                        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                        h1 { color: #28a745; text-align: center; }
                        .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                        .info { color: #666; margin: 20px 0; }
                        .cookies { background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>✓ 登录成功！</h1>
                        <div class="success">
                            模拟登录成功！Cookies已自动保存。
                        </div>
                        <div class="info">
                            <h3>已保存的Cookies：</h3>
                            <div class="cookies">
                                session_id: mock_session_123456<br>
                                user_token: mock_token_abcdef<br>
                                login_time: """ + str(int(time.time())) + """<br>
                                expires: """ + str(int(time.time()) + 86400) + """
                            </div>
                        </div>
                        <div class="info">
                            <p>这是模拟的登录成功页面。</p>
                            <p>在实际环境中，真实的Cookies将被保存并用于后续的数据抓取。</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # 保存模拟的cookies
                self._save_mock_cookies()
                
                return {
                    'success': True,
                    'message': '登录成功',
                    'login_success': True
                }
            
            return {
                'success': True,
                'message': f'已点击 {selector}'
            }
            
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return {
                'success': False,
                'error': f'点击失败: {str(e)}'
            }
    
    def _save_mock_cookies(self):
        """保存模拟的cookies"""
        try:
            mock_cookies = [
                {
                    'name': 'session_id',
                    'value': 'mock_session_123456',
                    'domain': '.javdb.com',
                    'path': '/',
                    'expires': int(time.time()) + 86400
                },
                {
                    'name': 'user_token',
                    'value': 'mock_token_abcdef',
                    'domain': '.javdb.com',
                    'path': '/',
                    'expires': int(time.time()) + 86400
                }
            ]
            
            cookies_data = {
                'cookies': mock_cookies,
                'timestamp': time.time(),
                'source': 'mock_login',
                'note': '这是模拟的cookies，仅用于测试'
            }
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"模拟Cookies已保存到 {self.cookies_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存模拟cookies失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理模拟浏览器资源")
        self.screenshot_html = ""
        self.current_page = "closed"
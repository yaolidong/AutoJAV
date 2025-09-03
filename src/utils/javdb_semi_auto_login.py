"""JavDB半自动登录模块 - 显示验证码让用户输入"""

import asyncio
import base64
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class JavDBSemiAutoLogin:
    """JavDB半自动登录管理器"""
    
    def __init__(self, config_dir: str = "/app/config"):
        """
        初始化登录管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_file = self.config_dir / "javdb_cookies.json"
        self.driver = None
        
    def get_login_page_with_captcha(self) -> Dict[str, any]:
        """
        获取登录页面和验证码图片
        
        Returns:
            包含验证码图片和session信息的字典
        """
        try:
            # 获取代理配置
            proxy = self._get_proxy_config()
            
            # 使用selenium_helper创建driver
            try:
                from .selenium_helper import get_chrome_driver
                logger.info("使用selenium_helper创建Chrome驱动...")
                self.driver = get_chrome_driver(headless=True, proxy=proxy)
                logger.info("成功创建Chrome驱动")
            except Exception as e:
                logger.error(f"创建Chrome驱动失败: {e}")
                raise Exception(f"无法启动浏览器: {str(e)}")
            
            self.driver.set_page_load_timeout(30)
            
            # 访问登录页面
            logger.info("访问JavDB登录页面...")
            self.driver.get("https://javdb.com/login")
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # 获取验证码图片
            captcha_element = self.driver.find_element(By.CSS_SELECTOR, "img.captcha-image, img[alt*='captcha'], img[src*='captcha']")
            
            # 截取验证码图片
            captcha_base64 = captcha_element.screenshot_as_base64
            
            # 获取session信息
            session_info = {
                'cookies': self.driver.get_cookies(),
                'session_id': self.driver.session_id
            }
            
            return {
                'success': True,
                'captcha_image': f"data:image/png;base64,{captcha_base64}",
                'session_info': session_info,
                'message': '验证码获取成功，请输入验证码'
            }
            
        except TimeoutException:
            logger.error("访问JavDB登录页面超时")
            return {
                'success': False,
                'error': 'JavDB无法访问。请配置代理后重试。'
            }
        except NoSuchElementException:
            logger.error("找不到验证码图片")
            return {
                'success': False,
                'error': '找不到验证码图片，页面结构可能已变更'
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取验证码失败: {error_msg}")
            
            # 提供更友好的错误信息
            if 'ERR_CONNECTION' in error_msg or 'ERR_NAME_NOT_RESOLVED' in error_msg:
                return {
                    'success': False,
                    'error': 'JavDB无法连接。请检查网络连接并配置代理。'
                }
            elif 'ERR_TUNNEL_CONNECTION_FAILED' in error_msg:
                return {
                    'success': False,
                    'error': '代理连接失败。请检查代理设置是否正确。'
                }
            else:
                return {
                    'success': False,
                    'error': f'获取验证码失败: {error_msg[:200]}'  # 限制错误信息长度
                }
    
    def submit_login(self, username: str, password: str, captcha: str) -> Dict[str, any]:
        """
        提交登录表单
        
        Args:
            username: 用户名
            password: 密码
            captcha: 验证码
            
        Returns:
            登录结果
        """
        try:
            if not self.driver:
                return {
                    'success': False,
                    'error': '请先获取验证码'
                }
            
            # 填写表单
            logger.info("填写登录表单...")
            
            # 输入用户名
            username_input = self.driver.find_element(By.NAME, "username")
            username_input.clear()
            username_input.send_keys(username)
            
            # 输入密码
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(password)
            
            # 输入验证码
            captcha_input = self.driver.find_element(By.NAME, "captcha")
            captcha_input.clear()
            captcha_input.send_keys(captcha)
            
            # 提交表单
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            submit_button.click()
            
            # 等待登录结果
            time.sleep(3)
            
            # 检查是否登录成功
            if "login" not in self.driver.current_url.lower():
                # 登录成功，保存cookies
                cookies = self.driver.get_cookies()
                self.save_cookies(cookies)
                
                logger.info("登录成功，cookies已保存")
                return {
                    'success': True,
                    'message': '登录成功，cookies已保存',
                    'cookies_count': len(cookies)
                }
            else:
                # 检查错误信息
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, ".alert-danger, .error-message")
                    error_message = error_element.text
                except:
                    error_message = "登录失败，请检查用户名、密码和验证码"
                
                # 如果验证码错误，获取新的验证码
                if "captcha" in error_message.lower() or "验证码" in error_message:
                    # 获取新的验证码
                    try:
                        captcha_element = self.driver.find_element(By.CSS_SELECTOR, "img.captcha-image, img[alt*='captcha']")
                        captcha_base64 = captcha_element.screenshot_as_base64
                        
                        return {
                            'success': False,
                            'error': error_message,
                            'new_captcha': f"data:image/png;base64,{captcha_base64}",
                            'retry': True
                        }
                    except:
                        pass
                
                return {
                    'success': False,
                    'error': error_message
                }
                
        except Exception as e:
            logger.error(f"提交登录失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def save_cookies(self, cookies: list) -> bool:
        """
        保存cookies到文件
        
        Args:
            cookies: cookies列表
            
        Returns:
            是否保存成功
        """
        try:
            # 保存cookies
            cookies_data = {
                'cookies': cookies,
                'timestamp': time.time(),
                'source': 'semi_auto_login'
            }
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cookies已保存到 {self.cookies_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存cookies失败: {e}")
            return False
    
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
    
    def cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
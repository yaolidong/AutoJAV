#!/usr/bin/env python3
"""
AutoJAV Web界面
提供配置管理、任务监控和实时日志查看功能
"""

import os
import sys
import json
import yaml
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import queue
import requests
from werkzeug.security import generate_password_hash, check_password_hash

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata
from src.scanner.file_scanner import FileScanner
from src.scrapers.scraper_factory import ScraperFactory
from src.utils.javdb_login import JavDBLoginManager
from src.utils.javdb_login_vnc import JavDBLoginVNC
from src.utils.pattern_manager import PatternManager, CodePattern

# 创建Flask应用
app = Flask(__name__, 
    static_folder='web/static',
    template_folder='web/templates'
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# API服务器地址
# 在host网络模式下使用localhost
API_HOST = os.environ.get('API_HOST', 'localhost')
API_PORT = os.environ.get('API_PORT', '5001')
API_BASE_URL = f'http://{API_HOST}:{API_PORT}'

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
config_file = Path('config/config.yaml')
task_queue = queue.Queue()
current_task = None
task_history = []
log_queue = queue.Queue(maxsize=1000)
vnc_login_manager = None  # VNC登录管理器

# 自定义日志处理器，发送到Web界面
class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'message': self.format(record),
            'module': record.module
        }
        try:
            log_queue.put_nowait(log_entry)
            socketio.emit('log_message', log_entry)
        except queue.Full:
            # 如果队列满了，移除最旧的
            try:
                log_queue.get_nowait()
                log_queue.put_nowait(log_entry)
            except:
                pass

# 添加WebSocket日志处理器
ws_handler = WebSocketLogHandler()
ws_handler.setLevel(logging.INFO)
ws_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(ws_handler)

def load_config():
    """加载配置文件 - 支持YAML和TOML格式"""
    # Try app_config.yaml first (our YAML config)
    app_config_file = Path('config/app_config.yaml')
    if app_config_file.exists():
        with open(app_config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # Fallback to config.yaml
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check if it's TOML format
            if content.strip().startswith('['):
                # Return default config for TOML format
                return {
                    'javdb': {
                        'username': '',
                        'password': '',
                        'cookies_file': '/app/config/javdb_cookies.json'
                    },
                    'directories': {
                        'source': '/app/source',
                        'target': '/app/target',
                        'config': '/app/config',
                        'logs': '/app/logs'
                    },
                    'selenium': {
                        'grid_url': 'http://localhost:4444',
                        'vnc_url': 'http://localhost:7900',
                        'browser': 'chrome',
                        'headless': False,
                        'timeout': 30
                    },
                    'processing': {
                        'max_concurrent_files': 2,
                        'max_concurrent_requests': 2,
                        'max_concurrent_downloads': 2
                    },
                    'api': {
                        'host': '0.0.0.0',
                        'port': 5555
                    },
                    'web': {
                        'host': '0.0.0.0',
                        'port': 8899
                    }
                }
            else:
                # It's YAML format
                return yaml.safe_load(content)
    
    # Return default config if no file found
    return {
        'directories': {
            'source': './source',
            'target': './organized'
        },
        'scraping': {
            'priority': ['javdb', 'javlibrary'],
            'max_concurrent_files': 2,
            'retry_attempts': 3,
            'timeout': 30
        },
        'organization': {
            'naming_pattern': '{actress}/{code}/{code}.{ext}',
            'conflict_resolution': 'rename',
            'download_images': True,
            'save_metadata': True,
            'safe_mode': True
        },
        'browser': {
            'headless': True,
            'timeout': 30
        },
        'network': {
            'proxy_url': '',
            'max_concurrent_requests': 2
        },
        'logging': {
            'level': 'INFO'
        }
    }

def save_config(config):
    """保存配置文件"""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    logger.info("配置已保存")

# 路由定义

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/patterns')
def patterns_page():
    """正则表达式管理页面"""
    return render_template('patterns.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    config = load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        new_config = request.json
        save_config(new_config)
        return jsonify({'success': True, 'message': '配置更新成功'})
    except Exception as e:
        logger.error(f"配置更新失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

# Initialize pattern manager (will auto-detect the correct path)
pattern_manager = PatternManager()

@app.route('/api/directories', methods=['GET'])
def get_directories():
    """获取目录信息"""
    config = load_config()
    source_dir = Path(config['directories']['source'])
    target_dir = Path(config['directories']['target'])
    
    # 扫描源目录
    source_files = []
    if source_dir.exists():
        for file in source_dir.glob('**/*.{mp4,avi,mkv,wmv,mov}'):
            source_files.append({
                'name': file.name,
                'path': str(file.relative_to(source_dir)),
                'size': file.stat().st_size,
                'size_mb': round(file.stat().st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
    
    # 统计目标目录
    target_stats = {
        'total_files': 0,
        'total_size': 0,
        'actresses': set()
    }
    
    if target_dir.exists():
        for file in target_dir.glob('**/*'):
            if file.is_file() and not file.suffix == '.json':
                target_stats['total_files'] += 1
                target_stats['total_size'] += file.stat().st_size
            if file.parent.parent == target_dir:  # 女优目录
                target_stats['actresses'].add(file.parent.name)
    
    return jsonify({
        'source': {
            'path': str(source_dir),
            'exists': source_dir.exists(),
            'files': source_files,
            'total': len(source_files)
        },
        'target': {
            'path': str(target_dir),
            'exists': target_dir.exists(),
            'total_files': target_stats['total_files'],
            'total_size_mb': round(target_stats['total_size'] / (1024 * 1024), 2),
            'actresses': list(target_stats['actresses'])
        }
    })

@app.route('/api/scan', methods=['POST'])
def scan_files():
    """扫描文件"""
    try:
        config = load_config()
        source_dir = Path(config.get('directories', {}).get('source', './source'))
        
        if not source_dir.exists():
            return jsonify({'success': False, 'error': '源目录不存在'}), 400
        
        # Get supported extensions from config
        supported_formats = config.get('supported_extensions', [
            '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v'
        ])
        
        scanner = FileScanner(str(source_dir), supported_formats)
        video_files = scanner.scan_directory()
        
        files_data = []
        for vf in video_files:
            files_data.append({
                'filename': vf.filename,
                'path': vf.file_path,
                'size_mb': round(vf.file_size / (1024 * 1024), 2),
                'extension': vf.extension,
                'detected_code': vf.detected_code
            })
        
        return jsonify({
            'success': True,
            'files': files_data,
            'total': len(files_data)
        })
    except Exception as e:
        logger.error(f"扫描失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/task/start', methods=['POST'])
def start_task():
    """启动刮削任务"""
    global current_task
    
    if current_task and current_task.get('status') == 'running':
        return jsonify({'success': False, 'error': '已有任务正在运行'}), 400
    
    try:
        task_config = request.json
        task_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        current_task = {
            'id': task_id,
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'config': task_config,
            'progress': 0,
            'processed': 0,
            'total': 0,
            'results': []
        }
        
        # 启动异步任务
        threading.Thread(target=run_scraping_task, args=(task_id,)).start()
        
        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        logger.error(f"启动任务失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/task/status', methods=['GET'])
def get_task_status():
    """获取任务状态"""
    if current_task:
        return jsonify(current_task)
    return jsonify({'status': 'idle'})

@app.route('/api/task/stop', methods=['POST'])
def stop_task():
    """停止任务"""
    global current_task
    
    if current_task and current_task.get('status') == 'running':
        current_task['status'] = 'stopping'
        return jsonify({'success': True, 'message': '正在停止任务'})
    
    return jsonify({'success': False, 'error': '没有运行中的任务'}), 400

@app.route('/api/task/history', methods=['GET'])
def get_task_history():
    """获取任务历史"""
    return jsonify(task_history[-20:])  # 返回最近20条

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    logs = []
    while not log_queue.empty():
        try:
            logs.append(log_queue.get_nowait())
        except:
            break
    return jsonify(logs)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    config = load_config()
    target_dir = Path(config['directories']['target'])
    
    stats = {
        'total_files': 0,
        'total_size_mb': 0,
        'by_actress': {},
        'by_studio': {},
        'by_date': {},
        'recent_files': []
    }
    
    if target_dir.exists():
        # 遍历所有文件
        for file in target_dir.glob('**/*'):
            if file.is_file() and not file.suffix == '.json':
                stats['total_files'] += 1
                file_size_mb = file.stat().st_size / (1024 * 1024)
                stats['total_size_mb'] += file_size_mb
                
                # 按女优统计（假设目录结构是 actress/code/file）
                if file.parent.parent != target_dir:
                    actress = file.parent.parent.name
                    if actress not in stats['by_actress']:
                        stats['by_actress'][actress] = 0
                    stats['by_actress'][actress] += 1
                
                # 最近文件
                stats['recent_files'].append({
                    'name': file.name,
                    'path': str(file.relative_to(target_dir)),
                    'size_mb': round(file_size_mb, 2),
                    'modified': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
        
        # 排序并限制最近文件数量
        stats['recent_files'].sort(key=lambda x: x['modified'], reverse=True)
        stats['recent_files'] = stats['recent_files'][:10]
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
    
    return jsonify(stats)

# Pattern Management API endpoints

@app.route('/api/patterns', methods=['GET'])
def get_patterns():
    """Get all regex patterns"""
    try:
        patterns = pattern_manager.get_all_patterns()
        return jsonify({'success': True, 'patterns': patterns})
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patterns', methods=['POST'])
def add_pattern():
    """Add a new regex pattern"""
    try:
        data = request.json
        pattern = CodePattern(
            name=data['name'],
            pattern=data['pattern'],
            format=data.get('format', '{0}-{1}'),
            description=data.get('description', ''),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0)
        )
        
        success = pattern_manager.add_pattern(pattern)
        if success:
            socketio.emit('pattern_added', {'pattern': pattern.to_dict()})
            return jsonify({'success': True, 'message': 'Pattern added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern with this name already exists'}), 400
            
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid pattern: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error adding pattern: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patterns/<pattern_name>', methods=['PUT'])
def update_pattern(pattern_name):
    """Update an existing regex pattern"""
    try:
        data = request.json
        pattern = CodePattern(
            name=data.get('name', pattern_name),
            pattern=data['pattern'],
            format=data.get('format', '{0}-{1}'),
            description=data.get('description', ''),
            enabled=data.get('enabled', True),
            priority=data.get('priority', 0)
        )
        
        success = pattern_manager.update_pattern(pattern_name, pattern)
        if success:
            socketio.emit('pattern_updated', {'pattern': pattern.to_dict()})
            return jsonify({'success': True, 'message': 'Pattern updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern not found'}), 404
            
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid pattern: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error updating pattern: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patterns/<pattern_name>', methods=['DELETE'])
def delete_pattern(pattern_name):
    """Delete a regex pattern"""
    try:
        success = pattern_manager.delete_pattern(pattern_name)
        if success:
            socketio.emit('pattern_deleted', {'name': pattern_name})
            return jsonify({'success': True, 'message': 'Pattern deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Pattern not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting pattern: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patterns/test', methods=['POST'])
def test_pattern():
    """Test a regex pattern against a sample string"""
    try:
        data = request.json
        pattern = data.get('pattern')
        test_string = data.get('test_string')
        
        if not pattern or not test_string:
            return jsonify({'success': False, 'error': 'Pattern and test string are required'}), 400
        
        result = pattern_manager.test_pattern(pattern, test_string)
        
        # Also test code extraction
        if result['matched'] and 'format' in data:
            try:
                groups = result['groups']
                formatted = data['format']
                for i, group in enumerate(groups):
                    if group is not None:
                        formatted = formatted.replace(f"{{{i}}}", group)
                result['formatted_code'] = formatted.upper()
            except Exception as e:
                result['format_error'] = str(e)
        
        return jsonify({'success': True, 'result': result})
        
    except Exception as e:
        logger.error(f"Error testing pattern: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patterns/extract', methods=['POST'])
def extract_code():
    """Extract code from a filename using current patterns"""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'success': False, 'error': 'Filename is required'}), 400
        
        code = pattern_manager.extract_code(filename)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'extracted_code': code,
            'code_found': code is not None
        })
        
    except Exception as e:
        logger.error(f"Error extracting code: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rename', methods=['POST'])
def rename_file():
    """重命名文件"""
    try:
        data = request.json
        old_path = Path(data.get('old_path'))
        new_name = data.get('new_name')
        
        if not old_path.exists():
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        # 构建新路径（保持在同一目录）
        new_path = old_path.parent / new_name
        
        # 检查新文件名是否已存在
        if new_path.exists() and new_path != old_path:
            return jsonify({'success': False, 'error': '文件名已存在'}), 400
        
        # 重命名文件
        old_path.rename(new_path)
        
        logger.info(f"文件重命名: {old_path} -> {new_path}")
        
        return jsonify({
            'success': True,
            'new_path': str(new_path),
            'new_name': new_name
        })
        
    except Exception as e:
        logger.error(f"重命名失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete', methods=['POST'])
def delete_files():
    """删除文件（支持批量）"""
    try:
        data = request.json
        paths = data.get('paths', [])
        
        if not paths:
            return jsonify({'success': False, 'error': '没有指定要删除的文件'}), 400
        
        deleted = []
        failed = []
        
        for path_str in paths:
            try:
                path = Path(path_str)
                if path.exists():
                    # 确保只能删除source目录下的文件
                    config = load_config()
                    source_dir = Path(config['directories']['source']).resolve()
                    file_path = path.resolve()
                    
                    # 安全检查：确保文件在source目录内
                    if not str(file_path).startswith(str(source_dir)):
                        failed.append({'path': str(path), 'error': '不允许删除源目录外的文件'})
                        continue
                    
                    path.unlink()
                    deleted.append(str(path))
                    logger.info(f"已删除文件: {path}")
                else:
                    failed.append({'path': str(path), 'error': '文件不存在'})
            except Exception as e:
                failed.append({'path': str(path_str), 'error': str(e)})
                logger.error(f"删除文件失败 {path_str}: {e}")
        
        return jsonify({
            'success': len(deleted) > 0,
            'deleted': deleted,
            'failed': failed,
            'message': f'成功删除 {len(deleted)} 个文件'
        })
        
    except Exception as e:
        logger.error(f"删除操作失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/javdb/proxy')
def javdb_proxy():
    """代理JavDB页面请求"""
    import requests
    
    url = request.args.get('url', 'https://javdb.com')
    
    # 获取代理配置
    config = load_config()
    proxy_url = config.get('network', {}).get('proxy_url')
    
    proxies = None
    if proxy_url:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    try:
        # 获取页面内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 从session获取cookies（如果有）
        cookies = session.get('javdb_cookies', {})
        
        response = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, timeout=30)
        
        # 保存cookies到session
        session['javdb_cookies'] = dict(response.cookies)
        
        # 修改页面内容，添加cookie监听脚本
        content = response.text
        
        # 注入JavaScript来监听登录状态
        inject_script = """
        <script>
        // 监听登录状态
        setInterval(function() {
            if (document.cookie.includes('_jdb_session')) {
                window.parent.postMessage({type: 'javdb_logged_in', cookies: document.cookie}, '*');
            }
        }, 2000);
        </script>
        """
        
        # 在</body>前注入脚本
        if '</body>' in content:
            content = content.replace('</body>', inject_script + '</body>')
        
        return content
        
    except Exception as e:
        logger.error(f"代理JavDB失败: {e}")
        return f"<html><body><h1>无法访问JavDB</h1><p>{str(e)}</p><p>请检查代理配置</p></body></html>"

@app.route('/api/javdb/login', methods=['POST'])
def javdb_login():
    """Manages JAVDB login via a VNC session."""
    global vnc_login_manager
    
    # 延迟初始化 VNC Login Manager
    if vnc_login_manager is None:
        try:
            config = load_config()
            config_dir = config.get('directories', {}).get('config', '/app/config')
            vnc_login_manager = JavDBLoginVNC(
                config_dir=config_dir
            )
            logger.info("VNC登录管理器初始化成功")
        except Exception as e:
            logger.error(f"VNC登录管理器初始化失败: {e}")
            return jsonify({'success': False, 'error': f'Failed to initialize VNC Login Manager: {e}'}), 500

    try:
        data = request.json or {}
        action = data.get('action', 'start')

        if action == 'start':
            # Generate login URL and instructions
            result = vnc_login_manager.generate_login_url()
            if result['success']:
                # Return VNC and noVNC URLs for the user to access
                result['vnc_url'] = 'http://localhost:7900'  # noVNC web interface
                result['selenium_url'] = 'http://localhost:4444'  # Selenium Grid
                result['message'] = 'Please open the VNC URL in a new tab to complete login'
            return jsonify(result)
        
        elif action == 'check':
            # Check and save cookies from browser
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from datetime import datetime
                import json
                import time
                
                config = load_config()
                config_dir = config.get('directories', {}).get('config', '/app/config')
                
                options = Options()
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                # Connect to the main Selenium Grid
                selenium_urls = ['http://localhost:4444/wd/hub']
                driver = None
                
                for selenium_url in selenium_urls:
                    try:
                        driver = webdriver.Remote(
                            command_executor=selenium_url,
                            options=options
                        )
                        logger.info(f"Connected to Selenium at {selenium_url}")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to connect to {selenium_url}: {e}")
                        continue
                
                if not driver:
                    return jsonify({
                        'success': False,
                        'error': 'Unable to connect to Selenium Grid. Please ensure browser is open.'
                    })
                
                # Get current URL to check if we're on JavDB
                current_url = driver.current_url
                if 'javdb.com' not in current_url:
                    driver.get('https://javdb.com')
                    time.sleep(2)
                
                # Get cookies
                cookies = driver.get_cookies()
                driver.quit()
                
                if not cookies:
                    return jsonify({
                        'success': False,
                        'error': 'No cookies found. Please log in to JavDB first.'
                    })
                
                # Save cookies
                cookie_file = Path(config_dir) / 'javdb_cookies.json'
                cookie_data = {
                    "cookies": cookies,
                    "timestamp": datetime.now().isoformat(),
                    "domain": "https://javdb.com"
                }
                
                with open(cookie_file, 'w') as f:
                    json.dump(cookie_data, f, indent=2)
                
                # Check if logged in
                has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)
                
                if has_session:
                    return jsonify({
                        'success': True,
                        'message': 'Cookies已成功保存！',
                        'cookie_count': len(cookies)
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Cookies已保存，但未找到登录会话。请先在浏览器中登录JavDB。'
                    })
                    
            except Exception as e:
                logger.error(f"Error checking/saving cookies: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
        
        elif action == 'save':
            # Save cookies from current browser session
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from datetime import datetime
                import json
                import time
                
                options = Options()
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                # Connect to Selenium Grid
                driver = webdriver.Remote(
                    command_executor='http://localhost:4444/wd/hub',
                    options=options
                )
                
                # Navigate to JavDB to ensure we're on the right domain
                driver.get('https://javdb.com')
                time.sleep(2)
                
                # Get cookies
                cookies = driver.get_cookies()
                
                # Save cookies
                cookie_file = Path(config_dir) / 'javdb_cookies.json'
                cookie_data = {
                    "cookies": cookies,
                    "timestamp": datetime.now().isoformat(),
                    "domain": "https://javdb.com"
                }
                
                with open(cookie_file, 'w') as f:
                    json.dump(cookie_data, f, indent=2)
                
                driver.quit()
                
                # Check if logged in
                has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)
                
                return jsonify({
                    'success': True,
                    'cookie_count': len(cookies),
                    'has_session': has_session,
                    'message': 'Cookies saved successfully' if has_session else 'Cookies saved but no session found'
                })
            except Exception as e:
                logger.error(f"Failed to save cookies: {e}")
                return jsonify({'success': False, 'error': str(e)})

        else:
            return jsonify({'success': False, 'error': f'Unknown action: {action}'})

    except Exception as e:
        logger.error(f"VNC login operation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/javdb/cookie-status', methods=['GET'])
def javdb_cookie_status():
    """获取JavDB cookie状态"""
    try:
        config = load_config()
        config_dir = config.get('directories', {}).get('config', '/app/config')
        login_manager = JavDBLoginManager(config_dir=config_dir)
        status = login_manager.get_cookie_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"获取cookie状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/javdb/verify-cookies', methods=['POST'])
def verify_javdb_cookies():
    """验证保存的JavDB cookies是否有效"""
    try:
        config = load_config()
        config_dir = config.get('directories', {}).get('config', '/app/config')
        
        # 使用增强的验证方法
        from src.utils.javdb_cookie_import import JavDBCookieImporter
        importer = JavDBCookieImporter(config_dir=config_dir)
        
        # 先尝试修复格式
        importer.fix_cookie_format()
        
        # 然后验证
        result = importer.verify_cookies_enhanced()
        
        return jsonify({
            'success': True,
            'valid': result['valid'],
            'logged_in': result['logged_in'],
            'message': 'Cookies有效' if result['valid'] else 'Cookies无效或已过期',
            'details': result.get('details', {})
        })
        
    except Exception as e:
        logger.error(f"验证cookies失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/javdb/clear-cookies', methods=['POST'])
def clear_javdb_cookies():
    """清除保存的JavDB cookies"""
    try:
        config = load_config()
        config_dir = config.get('directories', {}).get('config', '/app/config')
        login_manager = JavDBLoginManager(config_dir=config_dir)
        
        success = login_manager.clear_cookies()
        
        return jsonify({
            'success': success,
            'message': 'Cookies已清除' if success else '清除失败'
        })
        
    except Exception as e:
        logger.error(f"清除cookies失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_file():
    """刮削单个文件（代理到主容器）"""
    try:
        data = request.json
        
        # 调用主刮削容器的API
        import requests
        
        # 在host网络模式下使用localhost
        scraper_api_url = f"{API_BASE_URL}/api/scrape"
        
        try:
            response = requests.post(
                scraper_api_url,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': f'刮削服务返回错误: {response.status_code}'
                }), 500
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到刮削服务")
            return jsonify({
                'success': False,
                'error': '刮削服务不可用，请确保主容器正在运行'
            }), 503
            
    except Exception as e:
        logger.error(f"刮削文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_files():
    """处理文件（调用主刮削容器）"""
    try:
        data = request.json
        files = data.get('files', [])
        
        if not files:
            return jsonify({'success': False, 'error': '没有指定要处理的文件'}), 400
        
        # 调用主刮削容器的API
        import requests
        
        # 使用Docker容器名称作为主机名
        scraper_api_url = f"{API_BASE_URL}/api/process"
        
        try:
            response = requests.post(
                scraper_api_url,
                json={'files': files},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': f'刮削服务返回错误: {response.status_code}'
                }), 500
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到刮削服务，尝试本地处理")
            # 如果无法连接到主容器，返回错误
            return jsonify({
                'success': False,
                'error': '刮削服务不可用，请确保主容器正在运行'
            }), 503
            
    except Exception as e:
        logger.error(f"处理文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket事件处理

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    logger.info('客户端已断开')

# 任务执行函数

def run_scraping_task(task_id):
    """运行刮削任务"""
    global current_task, task_history
    
    try:
        logger.info(f"开始执行任务 {task_id}")
        config = load_config()
        
        # 扫描文件
        supported_formats = config.get('supported_extensions', [
            '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v', '.ts', '.m2ts'
        ])
        scanner = FileScanner(config['directories']['source'], supported_formats)
        video_files = scanner.scan_directory()
        
        current_task['total'] = len(video_files)
        
        # 创建整理器
        organizer = FileOrganizer(
            target_directory=config['directories']['target'],
            naming_pattern=config['organization'].get('naming_pattern', '{actress}/{code}/{code}.{ext}'),
            conflict_resolution=ConflictResolution[config['organization'].get('conflict_resolution', 'rename').upper()],
            create_metadata_files=config['organization'].get('save_metadata', True),
            safe_mode=config['organization'].get('safe_mode', True)
        )
        
        # 准备要处理的文件列表
        files_to_process = []
        for video_file in video_files:
            files_to_process.append({
                'filename': video_file.filename,
                'path': str(video_file.file_path),
                'extension': video_file.extension,
                'size': video_file.file_size,
                'detected_code': video_file.detected_code
            })
        
        # 调用主刮削容器的API
        import requests
        scraper_api_url = f"{API_BASE_URL}/api/process"
        
        logger.info(f"调用主刮削容器API处理 {len(files_to_process)} 个文件")
        
        try:
            # 发送处理请求到主刮削容器
            response = requests.post(
                scraper_api_url,
                json={'files': files_to_process},
                timeout=300  # 5分钟超时
            )
            
            if response.status_code == 200:
                api_result = response.json()
                
                if api_result.get('success'):
                    results = api_result.get('results', [])
                    
                    # 更新任务进度
                    for i, result in enumerate(results):
                        current_task['processed'] = i + 1
                        current_task['progress'] = int((i + 1) / len(results) * 100)
                        current_task['results'].append({
                            'file': result.get('file'),
                            'success': result.get('success'),
                            'message': result.get('message', ''),
                            'metadata': result.get('metadata')
                        })
                        
                        # 发送进度更新
                        socketio.emit('task_progress', {
                            'task_id': task_id,
                            'progress': current_task['progress'],
                            'processed': current_task['processed'],
                            'total': current_task['total']
                        })
                        
                        # 记录处理结果
                        if result.get('success'):
                            logger.info(f"成功处理: {result.get('file')}")
                            if result.get('metadata'):
                                actresses = result['metadata'].get('actresses', [])
                                if actresses and actresses[0] != "未知女优":
                                    logger.info(f"女优: {', '.join(actresses)}")
                        else:
                            logger.error(f"处理失败: {result.get('file')} - {result.get('error')}")
                else:
                    logger.error(f"API处理失败: {api_result.get('error')}")
                    raise Exception(api_result.get('error'))
            else:
                logger.error(f"API请求失败: HTTP {response.status_code}")
                raise Exception(f"API请求失败: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到主刮削容器，使用本地处理（无元数据）")
            # 如果API不可用，回退到本地处理（但不会有元数据）
            for i, video_file in enumerate(video_files):
                if current_task['status'] == 'stopping':
                    break
                
                metadata = MovieMetadata(
                    code=video_file.detected_code or "UNKNOWN",
                    title=f"影片 - {video_file.filename}",
                    actresses=["未知女优"],
                    release_date=datetime.now().date(),
                    studio="Unknown Studio"
                )
                
                result = organizer.organize_file(video_file, metadata)
                
                current_task['processed'] = i + 1
                current_task['progress'] = int((i + 1) / len(video_files) * 100)
                current_task['results'].append({
                    'file': video_file.filename,
                    'success': result['success'],
                    'message': result.get('message', '')
                })
        except Exception as e:
            logger.error(f"处理过程中出错: {e}")
            raise
        
        # 任务完成
        current_task['status'] = 'completed'
        current_task['end_time'] = datetime.now().isoformat()
        
        # 添加到历史
        task_history.append(current_task.copy())
        logger.info(f"任务 {task_id} 完成")
        
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        current_task['status'] = 'failed'
        current_task['error'] = str(e)
        current_task['end_time'] = datetime.now().isoformat()
        task_history.append(current_task.copy())

# 启动应用

# ==================== 历史记录API代理 ====================

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取刮削历史"""
    try:
        # 转发请求到主API服务器
        params = request.args.to_dict()
        response = requests.get(f'{API_BASE_URL}/api/history', params=params, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'success': False, 'error': 'Failed to get history'}), response.status_code
            
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    """获取历史统计"""
    try:
        response = requests.get(f'{API_BASE_URL}/api/history/stats', timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'success': False, 'error': 'Failed to get stats'}), response.status_code
            
    except Exception as e:
        logger.error(f"获取历史统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/export', methods=['GET'])
def export_history():
    """导出历史记录"""
    try:
        response = requests.get(f'{API_BASE_URL}/api/history/export', stream=True, timeout=30)
        
        if response.status_code == 200:
            # 流式传输文件
            def generate():
                for chunk in response.iter_content(chunk_size=4096):
                    yield chunk
            
            return Response(
                generate(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': 'attachment; filename=scrape_history.csv'
                }
            )
        else:
            return jsonify({'success': False, 'error': 'Failed to export history'}), response.status_code
            
    except Exception as e:
        logger.error(f"导出历史记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """清理历史记录"""
    try:
        data = request.json
        response = requests.post(f'{API_BASE_URL}/api/history/clear', json=data, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'success': False, 'error': 'Failed to clear history'}), response.status_code
            
    except Exception as e:
        logger.error(f"清理历史记录失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 确保必要的目录存在
    Path('web/static').mkdir(parents=True, exist_ok=True)
    Path('web/templates').mkdir(parents=True, exist_ok=True)
    Path('config').mkdir(parents=True, exist_ok=True)
    Path('logs').mkdir(parents=True, exist_ok=True)
    
    # 初始化VNC登录管理器
    try:
        config = load_config()
        config_dir = config.get('directories', {}).get('config', '/app/config')
        vnc_login_manager = JavDBLoginVNC(
            config_dir=config_dir
        )
        logger.info("VNC登录管理器初始化成功")
    except Exception as e:
        logger.error(f"VNC登录管理器初始化失败: {e}")
        vnc_login_manager = None
    
    # 启动应用
    logger.info("启动AutoJAV Web界面...")
    # 从环境变量获取端口，默认8080
    web_port = int(os.environ.get('WEB_PORT', '8080'))
    socketio.run(app, host='0.0.0.0', port=web_port, debug=True, allow_unsafe_werkzeug=True)

@app.route('/api/scrape', methods=['POST'])
def scrape_file():
    """刮削单个文件（代理到主容器）"""
    try:
        data = request.json
        
        # 调用主刮削容器的API
        import requests
        
        # 在host网络模式下使用localhost
        scraper_api_url = f"{API_BASE_URL}/api/scrape"
        
        try:
            response = requests.post(
                scraper_api_url,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': f'刮削服务返回错误: {response.status_code}'
                }), 500
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到刮削服务")
            return jsonify({
                'success': False,
                'error': '刮削服务不可用，请确保主容器正在运行'
            }), 503
            
    except Exception as e:
        logger.error(f"刮削文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_files():
    """处理文件（调用主刮削容器）"""
    try:
        data = request.json
        files = data.get('files', [])
        
        if not files:
            return jsonify({'success': False, 'error': '没有指定要处理的文件'}), 400
        
        # 调用主刮削容器的API
        import requests
        
        # 使用Docker容器名称作为主机名
        scraper_api_url = f"{API_BASE_URL}/api/process"
        
        try:
            response = requests.post(
                scraper_api_url,
                json={'files': files},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': f'刮削服务返回错误: {response.status_code}'
                }), 500
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到刮削服务，尝试本地处理")
            # 如果无法连接到主容器，返回错误
            return jsonify({
                'success': False,
                'error': '刮削服务不可用，请确保主容器正在运行'
            }), 503
            
    except Exception as e:
        logger.error(f"处理文件失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# WebSocket事件处理

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    logger.info('客户端已断开')

# 任务执行函数

def run_scraping_task(task_id):
    """运行刮削任务"""
    global current_task, task_history
    
    try:
        logger.info(f"开始执行任务 {task_id}")
        config = load_config()
        
        # 扫描文件
        supported_formats = config.get('supported_extensions', [
            '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v', '.ts', '.m2ts'
        ])
        scanner = FileScanner(config['directories']['source'], supported_formats)
        video_files = scanner.scan_directory()
        
        current_task['total'] = len(video_files)
        
        # 创建整理器
        organizer = FileOrganizer(
            target_directory=config['directories']['target'],
            naming_pattern=config['organization'].get('naming_pattern', '{actress}/{code}/{code}.{ext}'),
            conflict_resolution=ConflictResolution[config['organization'].get('conflict_resolution', 'rename').upper()],
            create_metadata_files=config['organization'].get('save_metadata', True),
            safe_mode=config['organization'].get('safe_mode', True)
        )
        
        # 准备要处理的文件列表
        files_to_process = []
        for video_file in video_files:
            files_to_process.append({
                'filename': video_file.filename,
                'path': str(video_file.file_path),
                'extension': video_file.extension,
                'size': video_file.file_size,
                'detected_code': video_file.detected_code
            })
        
        # 调用主刮削容器的API
        import requests
        scraper_api_url = f"{API_BASE_URL}/api/process"
        
        logger.info(f"调用主刮削容器API处理 {len(files_to_process)} 个文件")
        
        try:
            # 发送处理请求到主刮削容器
            response = requests.post(
                scraper_api_url,
                json={'files': files_to_process},
                timeout=300  # 5分钟超时
            )
            
            if response.status_code == 200:
                api_result = response.json()
                
                if api_result.get('success'):
                    results = api_result.get('results', [])
                    
                    # 更新任务进度
                    for i, result in enumerate(results):
                        current_task['processed'] = i + 1
                        current_task['progress'] = int((i + 1) / len(results) * 100)
                        current_task['results'].append({
                            'file': result.get('file'),
                            'success': result.get('success'),
                            'message': result.get('message', ''),
                            'metadata': result.get('metadata')
                        })
                        
                        # 发送进度更新
                        socketio.emit('task_progress', {
                            'task_id': task_id,
                            'progress': current_task['progress'],
                            'processed': current_task['processed'],
                            'total': current_task['total']
                        })
                        
                        # 记录处理结果
                        if result.get('success'):
                            logger.info(f"成功处理: {result.get('file')}")
                            if result.get('metadata'):
                                actresses = result['metadata'].get('actresses', [])
                                if actresses and actresses[0] != "未知女优":
                                    logger.info(f"女优: {', '.join(actresses)}")
                        else:
                            logger.error(f"处理失败: {result.get('file')} - {result.get('error')}")
                else:
                    logger.error(f"API处理失败: {api_result.get('error')}")
                    raise Exception(api_result.get('error'))
            else:
                logger.error(f"API请求失败: HTTP {response.status_code}")
                raise Exception(f"API请求失败: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error("无法连接到主刮削容器，使用本地处理（无元数据）")
            # 如果API不可用，回退到本地处理（但不会有元数据）
            for i, video_file in enumerate(video_files):
                if current_task['status'] == 'stopping':
                    break
                
                metadata = MovieMetadata(
                    code=video_file.detected_code or "UNKNOWN",
                    title=f"影片 - {video_file.filename}",
                    actresses=["未知女优"],
                    release_date=datetime.now().date(),
                    studio="Unknown Studio"
                )
                
                result = organizer.organize_file(video_file, metadata)
                
                current_task['processed'] = i + 1
                current_task['progress'] = int((i + 1) / len(video_files) * 100)
                current_task['results'].append({
                    'file': video_file.filename,
                    'success': result['success'],
                    'message': result.get('message', '')
                })
        except Exception as e:
            logger.error(f"处理过程中出错: {e}")
            raise
        
        # 任务完成
        current_task['status'] = 'completed'
        current_task['end_time'] = datetime.now().isoformat()
        
        # 添加到历史
        task_history.append(current_task.copy())
        logger.info(f"任务 {task_id} 完成")
        
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        current_task['status'] = 'failed'
        current_task['error'] = str(e)
        current_task['end_time'] = datetime.now().isoformat()
        task_history.append(current_task.copy())

# 启动应用

# ==================== 历史记录API代理 ====================

# @app.route('/api/history', methods=['GET'])
# def get_history():
#     """获取刮削历史"""
#     try:
        # 转发请求到主API服务器
#         params = request.args.to_dict()
#         response = requests.get(f'{API_BASE_URL}/api/history', params=params, timeout=10)
#         
#         if response.status_code == 200:
#             return jsonify(response.json())
#         else:
#             return jsonify({'success': False, 'error': 'Failed to get history'}), response.status_code
#             
#     except Exception as e:
#         logger.error(f"获取历史记录失败: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500
# 
# @app.route('/api/history/stats', methods=['GET'])
# def get_history_stats():
#     """获取历史统计"""
#     try:
#         response = requests.get(f'{API_BASE_URL}/api/history/stats', timeout=10)
#         
#         if response.status_code == 200:
#             return jsonify(response.json())
#         else:
#             return jsonify({'success': False, 'error': 'Failed to get stats'}), response.status_code
#             
#     except Exception as e:
#         logger.error(f"获取历史统计失败: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500
# 
# @app.route('/api/history/export', methods=['GET'])
# def export_history():
#     """导出历史记录"""
#     try:
#         response = requests.get(f'{API_BASE_URL}/api/history/export', stream=True, timeout=30)
#         
#         if response.status_code == 200:
            # 流式传输文件
#             def generate():
#                 for chunk in response.iter_content(chunk_size=4096):
#                     yield chunk
#             
#             return Response(
#                 generate(),
#                 mimetype='text/csv',
#                 headers={
#                     'Content-Disposition': 'attachment; filename=scrape_history.csv'
#                 }
#             )
#         else:
#             return jsonify({'success': False, 'error': 'Failed to export history'}), response.status_code
#             
#     except Exception as e:
#         logger.error(f"导出历史记录失败: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500
# 
# @app.route('/api/history/clear', methods=['POST'])
# def clear_history():
#     """清理历史记录"""
#     try:
#         data = request.json
#         response = requests.post(f'{API_BASE_URL}/api/history/clear', json=data, timeout=10)
#         
#         if response.status_code == 200:
#             return jsonify(response.json())
#         else:
#             return jsonify({'success': False, 'error': 'Failed to clear history'}), response.status_code
#             
#     except Exception as e:
#         logger.error(f"清理历史记录失败: {e}")
#         return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # 确保必要的目录存在
    Path('web/static').mkdir(parents=True, exist_ok=True)
    Path('web/templates').mkdir(parents=True, exist_ok=True)
    Path('config').mkdir(parents=True, exist_ok=True)
    Path('logs').mkdir(parents=True, exist_ok=True)
    
    # 初始化VNC登录管理器
    try:
        config = load_config()
        config_dir = config.get('directories', {}).get('config', '/app/config')
        vnc_login_manager = JavDBLoginVNC(
            config_dir=config_dir
        )
        logger.info("VNC登录管理器初始化成功")
    except Exception as e:
        logger.error(f"VNC登录管理器初始化失败: {e}")
        vnc_login_manager = None
    
    # 启动应用
    logger.info("启动AutoJAV Web界面...")
    # 从环境变量获取端口，默认8080
    web_port = int(os.environ.get('WEB_PORT', '8080'))
    socketio.run(app, host='0.0.0.0', port=web_port, debug=True, allow_unsafe_werkzeug=True)
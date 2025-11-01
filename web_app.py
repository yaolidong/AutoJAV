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
import re
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from copy import deepcopy
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
from src.utils.javdb_cookie_import import JavDBCookieImporter
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


DEFAULT_TOML_CONFIG: Dict[str, Any] = {
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
    'scrapers': {
        'javdb': {
            'base_url': 'https://javdb.com',
            'mirrors': []
        }
    },
    'scraping': {
        'success_criteria': {
            'require_actress': True,
            'require_title': True,
            'require_code': True,
            'images_optional': True
        }
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


DEFAULT_CONFIG: Dict[str, Any] = {
    'directories': {
        'source': './source',
        'target': './organized'
    },
    'scrapers': {
        'javdb': {
            'base_url': 'https://javdb.com',
            'mirrors': []
        }
    },
    'scraping': {
        'priority': ['javdb', 'javlibrary'],
        'max_concurrent_files': 2,
        'retry_attempts': 3,
        'timeout': 30,
        'success_criteria': {
            'require_actress': True,
            'require_title': True,
            'require_code': True,
            'images_optional': True
        }
    },
    'organization': {
        'naming_pattern': '{actress}/{code}/{code}.{ext}',
        'conflict_resolution': 'rename',
        'download_images': True,
        'save_metadata': True,
        'safe_mode': False,
        'actor_selection': 'first'
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


JAVDB_DEFAULT_URL = 'https://javdb.com'
JAVDB_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
LOGIN_MONITOR_SCRIPT = """
<script>
// 监听登录状态
setInterval(function() {
    if (document.cookie.includes('_jdb_session')) {
        window.parent.postMessage({type: 'javdb_logged_in', cookies: document.cookie}, '*');
    }
}, 2000);
</script>
"""

SELENIUM_DEFAULT_URLS = ['http://localhost:4444/wd/hub']
COOKIE_ATTRIBUTE_KEYS = {'path', 'domain', 'expires', 'max-age', 'samesite', 'comment', 'version'}

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

def _load_yaml_config(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def load_config():
    """加载配置文件 - 支持YAML和TOML格式"""
    app_config_file = Path('config/app_config.yaml')
    if app_config_file.exists():
        return _load_yaml_config(app_config_file)

    if config_file.exists():
        content = config_file.read_text(encoding='utf-8')
        if content.strip().startswith('['):
            return deepcopy(DEFAULT_TOML_CONFIG)
        return yaml.safe_load(content)

    return deepcopy(DEFAULT_CONFIG)

def save_config(config):
    """保存配置文件"""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    logger.info("配置已保存")


def _post_to_scraper_api(endpoint: str, payload: Dict[str, Any], *, timeout: int = 60) -> Dict[str, Any]:
    """向主刮削容器发送POST请求并返回JSON结果。"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError("无法连接到刮削服务") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"刮削服务请求失败: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"刮削服务返回错误: {response.status_code}")

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("刮削服务返回了无效的JSON响应") from exc

def _build_proxy_settings(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    proxy_url = config.get('network', {}).get('proxy_url')
    if not proxy_url:
        return None
    return {
        'http': proxy_url,
        'https': proxy_url
    }


def _resolve_config_dir(config: Dict[str, Any]) -> Path:
    return Path(config.get('directories', {}).get('config', '/app/config'))


def _get_javdb_base_url(config: Dict[str, Any]) -> str:
    scrapers_cfg = config.get('scrapers', {})
    if isinstance(scrapers_cfg, dict):
        javdb_cfg = scrapers_cfg.get('javdb', {})
        if isinstance(javdb_cfg, dict):
            base_url = javdb_cfg.get('base_url')
            if base_url:
                return base_url if base_url.startswith('http') else f'https://{base_url}'

    legacy_cfg = config.get('javdb', {})
    if isinstance(legacy_cfg, dict):
        base_url = legacy_cfg.get('base_url')
        if base_url:
            return base_url if base_url.startswith('http') else f'https://{base_url}'

    return JAVDB_DEFAULT_URL


def _get_cookie_domain(base_url: str) -> str:
    parsed = urlparse(base_url)
    domain = parsed.netloc or base_url
    domain = domain.split('/', 1)[0]
    domain = domain.split(':', 1)[0]
    if domain and not domain.startswith('.'):
        domain = f'.{domain}'
    return domain.lower() or '.javdb.com'


def _sanitize_cookie_domain(domain: Optional[str], default_domain: str) -> str:
    if not domain:
        return default_domain

    parsed = domain.strip()
    if parsed.startswith('http'):
        parsed = urlparse(parsed).netloc or parsed
    parsed = parsed.split(':', 1)[0]
    if parsed and not parsed.startswith('.'):
        parsed = f'.{parsed}'
    return parsed.lower() or default_domain


def _normalize_cookie_dict(cookie_data: Dict[str, Any], default_domain: str) -> Dict[str, Any]:
    name = str(cookie_data.get('name', '')).strip()
    if not name:
        raise ValueError('Cookie缺少名称')

    value = str(cookie_data.get('value', '')).strip()
    if value == '':
        raise ValueError(f'Cookie "{name}" 缺少值')

    def _to_bool(raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {'true', '1', 'yes', 'on'}
        return bool(raw)

    secure_flag = cookie_data.get('secure', cookie_data.get('Secure', False))
    http_only_flag = cookie_data.get('httpOnly', cookie_data.get('HttpOnly', False))

    normalized: Dict[str, Any] = {
        'name': name,
        'value': value,
        'domain': _sanitize_cookie_domain(cookie_data.get('domain'), default_domain),
        'path': cookie_data.get('path') or '/',
        'secure': _to_bool(secure_flag),
        'httpOnly': _to_bool(http_only_flag),
    }

    same_site = cookie_data.get('sameSite') or cookie_data.get('SameSite') or cookie_data.get('samesite')
    if same_site:
        normalized['sameSite'] = same_site

    expiry = (
        cookie_data.get('expiry')
        or cookie_data.get('expires')
        or cookie_data.get('Expires')
        or cookie_data.get('max-age')
        or cookie_data.get('Max-Age')
    )
    if expiry:
        try:
            normalized['expiry'] = int(expiry)
        except (ValueError, TypeError):
            # 保留原始字符串，供后续验证工具使用
            normalized['expiry'] = expiry

    return normalized


def _parse_cookie_string(cookie_string: str, default_domain: str) -> List[Dict[str, Any]]:
    text = (cookie_string or '').strip()
    if not text:
        return []

    lower_text = text.lower()
    if 'set-cookie:' in lower_text:
        segments = [seg.strip() for seg in re.split(r'(?i)set-cookie:', text) if seg.strip()]
    else:
        segments = [seg.strip() for seg in re.split(r'[\r\n]+', text) if seg.strip()]
        if not segments:
            segments = [text]

    cookies: List[Dict[str, Any]] = []
    additional_candidates: List[Dict[str, Any]] = []

    for segment in segments:
        parts = [p.strip() for p in segment.split(';') if p.strip()]
        if not parts:
            continue

        name_part = parts[0]
        if '=' not in name_part:
            continue

        name, value = name_part.split('=', 1)
        cookie_data: Dict[str, Any] = {'name': name, 'value': value}

        for attr in parts[1:]:
            lower_attr = attr.lower()
            if lower_attr == 'secure':
                cookie_data['secure'] = True
                continue
            if lower_attr == 'httponly':
                cookie_data['httpOnly'] = True
                continue
            if '=' not in attr:
                continue

            attr_name, attr_value = attr.split('=', 1)
            attr_name_lower = attr_name.strip().lower()
            attr_value = attr_value.strip()

            if attr_name_lower in COOKIE_ATTRIBUTE_KEYS:
                if attr_name_lower == 'path':
                    cookie_data['path'] = attr_value
                elif attr_name_lower == 'domain':
                    cookie_data['domain'] = attr_value
                elif attr_name_lower in {'expires', 'max-age'}:
                    cookie_data['expiry'] = attr_value
                elif attr_name_lower == 'samesite':
                    cookie_data['sameSite'] = attr_value
            else:
                additional_candidates.append({'name': attr_name.strip(), 'value': attr_value})

        cookies.append(_normalize_cookie_dict(cookie_data, default_domain))

    if not cookies:
        # 处理简单的 name=value; name2=value2 情况
        simple_pairs = [pair.strip() for pair in text.split(';') if pair.strip()]
        for pair in simple_pairs:
            if '=' not in pair:
                continue
            key, value = pair.split('=', 1)
            try:
                cookies.append(_normalize_cookie_dict({'name': key.strip(), 'value': value.strip()}, default_domain))
            except ValueError:
                continue
    else:
        for candidate in additional_candidates:
            try:
                cookies.append(_normalize_cookie_dict(candidate, default_domain))
            except ValueError:
                continue

    return cookies


def _deduplicate_cookies(cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for cookie in cookies:
        deduped[cookie['name']] = cookie
    return list(deduped.values())


def _parse_cookie_payload(payload: Any, default_domain: str) -> List[Dict[str, Any]]:
    if payload is None:
        raise ValueError('未提供Cookie数据')

    if isinstance(payload, str):
        text = payload.strip()
        if not text:
            raise ValueError('Cookie字符串为空')
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            cookies = _parse_cookie_string(text, default_domain)
        else:
            cookies = _parse_cookie_payload(parsed, default_domain)
        return _deduplicate_cookies(cookies)

    if isinstance(payload, list):
        cookies: List[Dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                cookies.append(_normalize_cookie_dict(item, default_domain))
            elif isinstance(item, str):
                cookies.extend(_parse_cookie_string(item, default_domain))
            else:
                raise ValueError('Cookie列表中的元素必须是对象或字符串')
        return _deduplicate_cookies(cookies)

    if isinstance(payload, dict):
        if 'cookies' in payload:
            return _parse_cookie_payload(payload['cookies'], default_domain)

        cookies: List[Dict[str, Any]] = []
        for name, value in payload.items():
            if isinstance(value, dict):
                cookie_data = {**value, 'name': name}
                cookies.append(_normalize_cookie_dict(cookie_data, default_domain))
            else:
                cookies.append(_normalize_cookie_dict({'name': name, 'value': value}, default_domain))
        return _deduplicate_cookies(cookies)

    raise ValueError('不支持的Cookie数据格式')


def _get_cookie_file_path(config: Dict[str, Any]) -> Path:
    config_dir = _resolve_config_dir(config)
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'javdb_cookies.json'


def _inject_login_monitor(content: str) -> str:
    if '</body>' in content:
        return content.replace('</body>', LOGIN_MONITOR_SCRIPT + '</body>')
    return content + LOGIN_MONITOR_SCRIPT

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
                if not path.exists():
                    failed.append({'path': str(path), 'error': '文件不存在'})
                    continue

                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

                deleted.append(str(path))
                logger.info(f"已删除: {path}")
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
    requested_url = request.args.get('url')
    config = load_config()
    base_url = _get_javdb_base_url(config)
    target_url = requested_url or base_url
    if requested_url and requested_url.startswith('/'):
        parsed = urlparse(base_url)
        target_url = f"{parsed.scheme or 'https'}://{parsed.netloc}{requested_url}"
    proxies = _build_proxy_settings(config)

    cookie_file = _resolve_config_dir(config) / 'javdb_cookies.json'
    cookies: Dict[str, str] = {}
    if cookie_file.exists():
        try:
            cookie_data = json.loads(cookie_file.read_text(encoding='utf-8'))
            for cookie in cookie_data.get('cookies', []):
                name = cookie.get('name')
                value = cookie.get('value')
                if name and value:
                    cookies[name] = value
        except Exception as exc:
            logger.warning(f"读取JavDB cookies失败: {exc}")

    try:
        response = requests.get(
            target_url,
            headers=JAVDB_HEADERS,
            proxies=proxies,
            cookies=cookies,
            timeout=30,
        )
        return _inject_login_monitor(response.text)
    except requests.RequestException as exc:
        logger.error(f"代理JavDB失败: {exc}")
        return (
            f"<html><body><h1>无法访问JavDB</h1><p>{str(exc)}</p>"
            "<p>请检查代理配置或Cookie是否有效</p></body></html>"
        )

@app.route('/api/javdb/cookies', methods=['POST'])
def save_javdb_cookies():
    """保存用户粘贴的JavDB cookies"""
    try:
        data = request.json or {}
        raw_cookies = data.get('cookies')
        if raw_cookies is None and 'raw' in data:
            raw_cookies = data['raw']
        if raw_cookies is None:
            raw_body = request.get_data(as_text=True).strip()
            raw_cookies = raw_body or None

        config = load_config()
        base_url = _get_javdb_base_url(config)
        default_domain = _get_cookie_domain(base_url)

        cookies = _parse_cookie_payload(raw_cookies, default_domain)
        if not cookies:
            raise ValueError('未解析到任何有效的Cookie')

        cookie_file = _get_cookie_file_path(config)
        cookie_data = {
            'cookies': cookies,
            'timestamp': datetime.now().isoformat(),
            'domain': base_url
        }
        cookie_file.write_text(json.dumps(cookie_data, indent=2, ensure_ascii=False), encoding='utf-8')

        has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)

        logger.info("已保存 %d 个 JavDB cookies (手动输入)", len(cookies))
        return jsonify({
            'success': True,
            'cookie_count': len(cookies),
            'has_session': has_session
        })

    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f"保存JavDB cookies失败: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 500

@app.route('/api/javdb/cookie-status', methods=['GET'])
def javdb_cookie_status():
    """获取JavDB cookie状态"""
    try:
        config = load_config()
        base_url = _get_javdb_base_url(config)
        cookie_file = _resolve_config_dir(config) / 'javdb_cookies.json'

        if not cookie_file.exists():
            return jsonify({'success': True, 'status': {'exists': False, 'domain': base_url}})

        data = json.loads(cookie_file.read_text(encoding='utf-8'))
        cookies = data.get('cookies', [])
        timestamp = data.get('timestamp')
        has_session = any(cookie.get('name') == '_jdb_session' for cookie in cookies)

        status = {
            'exists': True,
            'cookie_count': len(cookies),
            'has_session': has_session,
            'domain': data.get('domain', base_url)
        }

        if timestamp:
            status['timestamp'] = timestamp
            try:
                saved_dt = datetime.fromisoformat(timestamp)
                now = datetime.now(saved_dt.tzinfo) if saved_dt.tzinfo else datetime.now()
                status['age_days'] = max((now - saved_dt).days, 0)
            except ValueError:
                status['age_days'] = None

        return jsonify({'success': True, 'status': status})

    except Exception as e:
        logger.error(f"获取cookie状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/javdb/verify-cookies', methods=['POST'])
def verify_javdb_cookies():
    """验证保存的JavDB cookies是否有效"""
    try:
        config = load_config()
        config_dir = config.get('directories', {}).get('config', '/app/config')
        base_url = _get_javdb_base_url(config)
        importer = JavDBCookieImporter(config_dir=config_dir, base_url=base_url)
        
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
        cookie_file = _resolve_config_dir(config) / 'javdb_cookies.json'

        if cookie_file.exists():
            cookie_file.unlink()
            logger.info("已清除JavDB cookies")
            return jsonify({'success': True, 'message': 'Cookies已清除'})

        return jsonify({'success': True, 'message': '未找到Cookie文件，无需清理'})

    except Exception as e:
        logger.error(f"清除cookies失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scrape', methods=['POST'])
def scrape_file():
    """刮削单个文件（代理到主容器）"""
    try:
        payload = request.json or {}
        result = _post_to_scraper_api('/api/scrape', payload)
        return jsonify(result)
    except ConnectionError:
        logger.error("无法连接到刮削服务")
        return jsonify({
            'success': False,
            'error': '刮削服务不可用，请确保主容器正在运行'
        }), 503
    except Exception as exc:
        logger.error(f"刮削文件失败: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/process', methods=['POST'])
def process_files():
    """处理文件（调用主刮削容器）"""
    try:
        data = request.json or {}
        files = data.get('files', [])

        if not files:
            return jsonify({'success': False, 'error': '没有指定要处理的文件'}), 400

        result = _post_to_scraper_api('/api/process', {'files': files})
        return jsonify(result)
    except ConnectionError:
        logger.error("无法连接到刮削服务，尝试本地处理")
        return jsonify({
            'success': False,
            'error': '刮削服务不可用，请确保主容器正在运行'
        }), 503
    except Exception as exc:
        logger.error(f"处理文件失败: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 500

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


def _scan_video_files(config: Dict[str, Any]) -> List[VideoFile]:
    supported_formats = config.get('supported_extensions', [
        '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v', '.ts', '.m2ts'
    ])
    scanner = FileScanner(config['directories']['source'], supported_formats)
    return scanner.scan_directory()


def _build_processing_payload(video_files: List[VideoFile]) -> List[Dict[str, Any]]:
    return [
        {
            'filename': video_file.filename,
            'path': str(video_file.file_path),
            'extension': video_file.extension,
            'size': video_file.file_size,
            'detected_code': video_file.detected_code,
        }
        for video_file in video_files
    ]


def _create_file_organizer(config: Dict[str, Any]) -> FileOrganizer:
    organization = config.get('organization', {})
    return FileOrganizer(
        target_directory=config['directories']['target'],
        naming_pattern=organization.get('naming_pattern', '{actress}/{code}/{code}.{ext}'),
        conflict_resolution=ConflictResolution[organization.get('conflict_resolution', 'rename').upper()],
        create_metadata_files=organization.get('save_metadata', True),
        safe_mode=organization.get('safe_mode', False),
    )


def _append_task_result(task_id: str, processed: int, total: int, result: Dict[str, Any]) -> None:
    current_task['processed'] = processed
    current_task['progress'] = int(processed / total * 100) if total else 0
    current_task['results'].append(result)
    socketio.emit('task_progress', {
        'task_id': task_id,
        'progress': current_task['progress'],
        'processed': current_task['processed'],
        'total': total,
    })


def _process_remote_results(task_id: str, api_result: Dict[str, Any]) -> None:
    if not api_result.get('success'):
        error_message = api_result.get('error', '刮削服务处理失败')
        logger.error(f"API处理失败: {error_message}")
        raise Exception(error_message)

    results = api_result.get('results', [])
    total = len(results)

    for index, result in enumerate(results, start=1):
        _append_task_result(task_id, index, total, {
            'file': result.get('file'),
            'success': result.get('success'),
            'message': result.get('message', ''),
            'metadata': result.get('metadata'),
        })

        if result.get('success'):
            logger.info(f"成功处理: {result.get('file')}")
            metadata = result.get('metadata') or {}
            actresses = metadata.get('actresses', [])
            if actresses and actresses[0] != "未知女优":
                logger.info(f"女优: {', '.join(actresses)}")
        else:
            logger.error(f"处理失败: {result.get('file')} - {result.get('error')}")


def _process_local_files(task_id: str, video_files: List[VideoFile], organizer: FileOrganizer) -> None:
    total = len(video_files)
    for index, video_file in enumerate(video_files, start=1):
        if current_task.get('status') == 'stopping':
            break

        metadata = MovieMetadata(
            code=video_file.detected_code or 'UNKNOWN',
            title=f"影片 - {video_file.filename}",
            actresses=['未知女优'],
            release_date=datetime.now().date(),
            studio='Unknown Studio',
        )

        result = organizer.organize_file(video_file, metadata)
        _append_task_result(task_id, index, total, {
            'file': video_file.filename,
            'success': result['success'],
            'message': result.get('message', ''),
        })

def run_scraping_task(task_id):
    """运行刮削任务"""
    global current_task, task_history
    
    try:
        logger.info(f"开始执行任务 {task_id}")
        config = load_config()
        video_files = _scan_video_files(config)
        current_task['total'] = len(video_files)

        organizer = _create_file_organizer(config)
        files_to_process = _build_processing_payload(video_files)

        logger.info(f"调用主刮削容器API处理 {len(files_to_process)} 个文件")

        try:
            api_result = _post_to_scraper_api('/api/process', {'files': files_to_process}, timeout=300)
            _process_remote_results(task_id, api_result)
        except ConnectionError:
            logger.error("无法连接到主刮削容器，使用本地处理（无元数据）")
            _process_local_files(task_id, video_files, organizer)
        
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

    # 启动应用
    logger.info("启动AutoJAV Web界面...")
    # 从环境变量获取端口，默认8080
    web_port = int(os.environ.get('WEB_PORT', '8080'))
    socketio.run(app, host='0.0.0.0', port=web_port, debug=True, allow_unsafe_werkzeug=True)
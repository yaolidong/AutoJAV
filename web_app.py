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
from werkzeug.security import generate_password_hash, check_password_hash

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata
from src.scanner.file_scanner import FileScanner
from src.scrapers.scraper_factory import ScraperFactory

# 创建Flask应用
app = Flask(__name__, 
    static_folder='web/static',
    template_folder='web/templates'
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

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
    """加载配置文件"""
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
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
        source_dir = Path(config['directories']['source'])
        
        if not source_dir.exists():
            return jsonify({'success': False, 'error': '源目录不存在'}), 400
        
        scanner = FileScanner(str(source_dir))
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
        scanner = FileScanner(config['directories']['source'])
        video_files = scanner.scan_directory()
        
        current_task['total'] = len(video_files)
        
        # 创建整理器
        organizer = FileOrganizer(
            target_directory=config['directories']['target'],
            naming_pattern=config['organization']['naming_pattern'],
            conflict_resolution=ConflictResolution[config['organization']['conflict_resolution'].upper()],
            create_metadata_files=config['organization']['save_metadata'],
            safe_mode=config['organization']['safe_mode']
        )
        
        # 处理每个文件
        for i, video_file in enumerate(video_files):
            if current_task['status'] == 'stopping':
                logger.info("任务被用户停止")
                break
            
            logger.info(f"处理文件 {i+1}/{len(video_files)}: {video_file.filename}")
            
            # 这里应该调用实际的刮削器，但为了演示，使用模拟数据
            metadata = MovieMetadata(
                code=video_file.detected_code or "UNKNOWN",
                title=f"影片 - {video_file.filename}",
                actresses=["未知女优"],
                release_date=datetime.now().date(),
                studio="Unknown Studio"
            )
            
            # 整理文件
            result = organizer.organize_file(video_file, metadata)
            
            current_task['processed'] = i + 1
            current_task['progress'] = int((i + 1) / len(video_files) * 100)
            current_task['results'].append({
                'file': video_file.filename,
                'success': result['success'],
                'message': result.get('message', '')
            })
            
            # 发送进度更新
            socketio.emit('task_progress', {
                'task_id': task_id,
                'progress': current_task['progress'],
                'processed': current_task['processed'],
                'total': current_task['total']
            })
        
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

if __name__ == '__main__':
    # 确保必要的目录存在
    Path('web/static').mkdir(parents=True, exist_ok=True)
    Path('web/templates').mkdir(parents=True, exist_ok=True)
    Path('config').mkdir(parents=True, exist_ok=True)
    Path('logs').mkdir(parents=True, exist_ok=True)
    
    # 启动应用
    logger.info("启动AutoJAV Web界面...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
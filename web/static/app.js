// AutoJAV Web界面 JavaScript
// 处理所有前端交互逻辑

// WebSocket连接
let socket = null;
let currentConfig = {};
let taskRunning = false;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    initNavigation();
    loadConfig();
    loadDashboard();
    
    // 定时刷新
    setInterval(updateDashboard, 5000);
    setInterval(checkTaskStatus, 2000);
});

// WebSocket连接
function initWebSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket连接成功');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket连接断开');
        updateConnectionStatus(false);
    });
    
    socket.on('log_message', function(data) {
        appendLog(data);
    });
    
    socket.on('task_progress', function(data) {
        updateTaskProgress(data);
    });
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.innerHTML = '<i class="bi bi-circle-fill text-success"></i> 已连接';
    } else {
        statusEl.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> 未连接';
    }
}

// 导航初始化
function initNavigation() {
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            showPage(page);
            
            // 更新活动状态
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// 显示页面
function showPage(pageName) {
    // 隐藏所有页面
    document.querySelectorAll('.page-content').forEach(page => {
        page.style.display = 'none';
    });
    
    // 显示选中页面
    const pageEl = document.getElementById(`${pageName}-page`);
    if (pageEl) {
        pageEl.style.display = 'block';
        
        // 页面特定的初始化
        switch(pageName) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'config':
                loadConfig();
                break;
            case 'stats':
                loadStats();
                break;
        }
    }
}

// 加载仪表板
async function loadDashboard() {
    try {
        // 获取目录信息
        const dirResponse = await fetch('/api/directories');
        const dirData = await dirResponse.json();
        
        // 更新统计
        document.getElementById('stat-pending').textContent = dirData.source.total || 0;
        
        // 获取统计信息
        const statsResponse = await fetch('/api/stats');
        const statsData = await statsResponse.json();
        
        document.getElementById('stat-total-files').textContent = statsData.total_files || 0;
        document.getElementById('stat-total-size').textContent = 
            `${(statsData.total_size_mb / 1024).toFixed(1)} GB`;
        document.getElementById('stat-actresses').textContent = 
            Object.keys(statsData.by_actress || {}).length;
        
        // 更新最近文件
        updateRecentFiles(statsData.recent_files);
        
    } catch (error) {
        console.error('加载仪表板失败:', error);
    }
}

// 更新仪表板
async function updateDashboard() {
    if (document.getElementById('dashboard-page').style.display !== 'none') {
        loadDashboard();
    }
}

// 更新最近文件列表
function updateRecentFiles(files) {
    const container = document.getElementById('recent-files-list');
    
    if (!files || files.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无数据</p>';
        return;
    }
    
    let html = '<div class="list-group">';
    files.slice(0, 5).forEach(file => {
        html += `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${file.name}</strong>
                        <br><small class="text-muted">${file.path}</small>
                    </div>
                    <div>
                        <span class="badge bg-secondary">${file.size_mb} MB</span>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        currentConfig = await response.json();
        
        // 填充表单
        document.getElementById('config-source-dir').value = currentConfig.directories?.source || '';
        document.getElementById('config-target-dir').value = currentConfig.directories?.target || '';
        
        // 刮削设置
        const priority = currentConfig.scraping?.priority?.join(',') || 'javdb,javlibrary';
        document.getElementById('config-scraper-priority').value = priority;
        document.getElementById('config-max-concurrent').value = currentConfig.scraping?.max_concurrent_files || 2;
        document.getElementById('config-timeout').value = currentConfig.scraping?.timeout || 30;
        
        // 文件整理设置
        document.getElementById('config-naming-pattern').value = 
            currentConfig.organization?.naming_pattern || '{actress}/{code}/{code}.{ext}';
        document.getElementById('config-conflict-resolution').value = 
            currentConfig.organization?.conflict_resolution || 'rename';
        document.getElementById('config-safe-mode').checked = 
            currentConfig.organization?.safe_mode !== false;
        document.getElementById('config-download-images').checked = 
            currentConfig.organization?.download_images !== false;
        document.getElementById('config-save-metadata').checked = 
            currentConfig.organization?.save_metadata !== false;
        
    } catch (error) {
        console.error('加载配置失败:', error);
        showToast('加载配置失败', 'danger');
    }
}

// 保存配置
async function saveConfig() {
    try {
        // 收集表单数据
        const config = {
            directories: {
                source: document.getElementById('config-source-dir').value,
                target: document.getElementById('config-target-dir').value
            },
            scraping: {
                priority: document.getElementById('config-scraper-priority').value.split(','),
                max_concurrent_files: parseInt(document.getElementById('config-max-concurrent').value),
                timeout: parseInt(document.getElementById('config-timeout').value),
                retry_attempts: 3
            },
            organization: {
                naming_pattern: document.getElementById('config-naming-pattern').value,
                conflict_resolution: document.getElementById('config-conflict-resolution').value,
                safe_mode: document.getElementById('config-safe-mode').checked,
                download_images: document.getElementById('config-download-images').checked,
                save_metadata: document.getElementById('config-save-metadata').checked
            },
            browser: {
                headless: true,
                timeout: 30
            },
            network: {
                proxy_url: '',
                max_concurrent_requests: 2
            },
            logging: {
                level: 'INFO'
            }
        };
        
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        if (result.success) {
            showToast('配置保存成功', 'success');
            currentConfig = config;
        } else {
            showToast('配置保存失败: ' + result.error, 'danger');
        }
        
    } catch (error) {
        console.error('保存配置失败:', error);
        showToast('保存配置失败', 'danger');
    }
}

// 扫描文件
async function scanFiles() {
    try {
        const scanBtn = event.target;
        scanBtn.disabled = true;
        scanBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>扫描中...';
        
        const response = await fetch('/api/scan', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayScanResults(result.files);
            showToast(`扫描完成，找到 ${result.total} 个文件`, 'success');
        } else {
            showToast('扫描失败: ' + result.error, 'danger');
        }
        
    } catch (error) {
        console.error('扫描失败:', error);
        showToast('扫描失败', 'danger');
    } finally {
        const scanBtn = event.target;
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 扫描文件';
    }
}

// 显示扫描结果
function displayScanResults(files) {
    const container = document.getElementById('scan-results');
    
    if (!files || files.length === 0) {
        container.innerHTML = '<p class="text-muted">未找到视频文件</p>';
        return;
    }
    
    let html = '';
    files.forEach(file => {
        const codeClass = file.detected_code ? 'success' : 'warning';
        const codeText = file.detected_code || '未识别';
        
        html += `
            <div class="file-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${file.filename}</strong>
                        <br><small class="text-muted">${file.path}</small>
                    </div>
                    <div>
                        <span class="badge bg-${codeClass} me-2">${codeText}</span>
                        <span class="badge bg-secondary">${file.size_mb} MB</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 开始任务
async function startTask() {
    try {
        const response = await fetch('/api/task/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                config: currentConfig
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            taskRunning = true;
            document.getElementById('btn-start-task').style.display = 'none';
            document.getElementById('btn-stop-task').style.display = 'inline-block';
            showToast('任务已启动', 'success');
        } else {
            showToast('启动任务失败: ' + result.error, 'danger');
        }
        
    } catch (error) {
        console.error('启动任务失败:', error);
        showToast('启动任务失败', 'danger');
    }
}

// 停止任务
async function stopTask() {
    try {
        const response = await fetch('/api/task/stop', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('正在停止任务...', 'warning');
        }
        
    } catch (error) {
        console.error('停止任务失败:', error);
    }
}

// 检查任务状态
async function checkTaskStatus() {
    if (!taskRunning && document.getElementById('task-page').style.display === 'none') {
        return;
    }
    
    try {
        const response = await fetch('/api/task/status');
        const status = await response.json();
        
        if (status.status === 'running') {
            taskRunning = true;
            document.getElementById('btn-start-task').style.display = 'none';
            document.getElementById('btn-stop-task').style.display = 'inline-block';
            
            // 更新进度
            updateTaskProgress({
                progress: status.progress || 0,
                processed: status.processed || 0,
                total: status.total || 0
            });
            
            // 更新仪表板状态
            const statusDisplay = document.getElementById('task-status-display');
            if (statusDisplay) {
                statusDisplay.innerHTML = `
                    <div class="progress mb-2">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             style="width: ${status.progress}%">${status.progress}%</div>
                    </div>
                    <p>处理中: ${status.processed}/${status.total} 文件</p>
                `;
            }
            
        } else if (status.status === 'completed' || status.status === 'failed' || status.status === 'idle') {
            taskRunning = false;
            document.getElementById('btn-start-task').style.display = 'inline-block';
            document.getElementById('btn-stop-task').style.display = 'none';
            
            if (status.status === 'completed') {
                showToast('任务完成', 'success');
                loadTaskHistory();
            } else if (status.status === 'failed') {
                showToast('任务失败: ' + (status.error || '未知错误'), 'danger');
            }
            
            // 清除仪表板状态
            const statusDisplay = document.getElementById('task-status-display');
            if (statusDisplay) {
                statusDisplay.innerHTML = '<p class="text-muted">没有运行中的任务</p>';
            }
        }
        
    } catch (error) {
        console.error('检查任务状态失败:', error);
    }
}

// 更新任务进度
function updateTaskProgress(data) {
    const progressBar = document.getElementById('task-progress-bar');
    const taskInfo = document.getElementById('task-info');
    
    if (progressBar) {
        progressBar.style.width = `${data.progress}%`;
        progressBar.textContent = `${data.progress}%`;
    }
    
    if (taskInfo) {
        taskInfo.textContent = `处理中: ${data.processed}/${data.total} 文件`;
    }
}

// 加载任务历史
async function loadTaskHistory() {
    try {
        const response = await fetch('/api/task/history');
        const history = await response.json();
        
        const container = document.getElementById('task-history-list');
        
        if (!history || history.length === 0) {
            container.innerHTML = '<p class="text-muted">暂无任务历史</p>';
            return;
        }
        
        let html = '<div class="list-group">';
        history.reverse().forEach(task => {
            const statusClass = task.status === 'completed' ? 'success' : 
                               task.status === 'failed' ? 'danger' : 'warning';
            const statusText = task.status === 'completed' ? '完成' :
                              task.status === 'failed' ? '失败' : '中断';
            
            html += `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>任务 ${task.id}</strong>
                            <br><small class="text-muted">开始: ${new Date(task.start_time).toLocaleString()}</small>
                        </div>
                        <div>
                            <span class="badge bg-${statusClass}">${statusText}</span>
                            <span class="badge bg-secondary">${task.processed}/${task.total}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('加载任务历史失败:', error);
    }
}

// 添加日志
function appendLog(logData) {
    const container = document.getElementById('log-container');
    if (!container) return;
    
    const levelClass = logData.level || 'INFO';
    const timestamp = new Date(logData.timestamp).toLocaleTimeString();
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${levelClass}`;
    logEntry.innerHTML = `[${timestamp}] ${logData.message}`;
    
    container.appendChild(logEntry);
    
    // 自动滚动到底部
    container.scrollTop = container.scrollHeight;
    
    // 限制日志数量
    while (container.children.length > 500) {
        container.removeChild(container.firstChild);
    }
}

// 清空日志
function clearLogs() {
    const container = document.getElementById('log-container');
    container.innerHTML = '<div class="text-muted p-3">等待日志输出...</div>';
}

// 加载统计信息
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        // 按女优统计
        const actressContainer = document.getElementById('stats-by-actress');
        if (stats.by_actress && Object.keys(stats.by_actress).length > 0) {
            let html = '<ul class="list-group">';
            Object.entries(stats.by_actress)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .forEach(([actress, count]) => {
                    html += `
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            ${actress}
                            <span class="badge bg-primary rounded-pill">${count}</span>
                        </li>
                    `;
                });
            html += '</ul>';
            actressContainer.innerHTML = html;
        } else {
            actressContainer.innerHTML = '<p class="text-muted">暂无数据</p>';
        }
        
        // 最近文件
        const recentContainer = document.getElementById('stats-recent-files');
        if (stats.recent_files && stats.recent_files.length > 0) {
            let html = '<ul class="list-group">';
            stats.recent_files.slice(0, 10).forEach(file => {
                const date = new Date(file.modified).toLocaleDateString();
                html += `
                    <li class="list-group-item">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${file.name}</strong>
                                <br><small class="text-muted">${file.path}</small>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-secondary">${file.size_mb} MB</span>
                                <br><small class="text-muted">${date}</small>
                            </div>
                        </div>
                    </li>
                `;
            });
            html += '</ul>';
            recentContainer.innerHTML = html;
        } else {
            recentContainer.innerHTML = '<p class="text-muted">暂无数据</p>';
        }
        
    } catch (error) {
        console.error('加载统计信息失败:', error);
    }
}

// 显示Toast通知
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 3000
    });
    
    toast.show();
    
    // 自动清理
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}
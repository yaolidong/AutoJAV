// AutoJAV Web界面 JavaScript
// 处理所有前端交互逻辑

// WebSocket连接
let socket = null;
let currentConfig = {};
let taskRunning = false;
let monitoringEnabled = false;
let monitoringInterval = null;

// 声明历史相关函数（稍后定义）
let loadHistory, searchHistory, refreshHistory, exportHistory, clearHistory, filterHistory, viewHistoryDetail;
let loadStats;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    initNavigation();
    loadConfig();
    loadDashboard();
    
    // 定时刷新
    setInterval(updateDashboard, 5000);
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
    
    // Task progress 事件已废弃
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
            case 'history':
                if (typeof loadHistory === 'function') {
                    loadHistory();
                } else {
                    console.log('History function not yet loaded');
                }
                break;
            case 'stats':
                if (typeof loadStats === 'function') {
                    loadStats();
                } else {
                    console.log('Stats function not yet loaded');
                }
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
async function scanFiles(event) {
    try {
        const scanBtn = event ? event.target : document.querySelector('[onclick*="scanFiles"]');
        if (scanBtn) {
            scanBtn.disabled = true;
            scanBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>刷新中...';
        }
        
        const response = await fetch('/api/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
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
        const scanBtn = event ? event.target : document.querySelector('[onclick*="scanFiles"]');
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 刷新列表';
        }
    }
}

// 显示扫描结果（增强版文件列表）
function displayScanResults(files) {
    const tableBody = document.getElementById('file-list-body');
    const table = document.getElementById('file-list-table');
    const emptyState = document.getElementById('empty-state');
    const selectAllBtn = document.getElementById('select-all-btn');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const scrapeSelectedBtn = document.getElementById('scrape-selected-btn');
    
    if (!files || files.length === 0) {
        table.style.display = 'none';
        emptyState.style.display = 'block';
        selectAllBtn.style.display = 'none';
        deleteSelectedBtn.style.display = 'none';
        scrapeSelectedBtn.style.display = 'none';
        return;
    }
    
    // 显示表格和批量操作按钮
    table.style.display = 'table';
    emptyState.style.display = 'none';
    selectAllBtn.style.display = 'inline-block';
    deleteSelectedBtn.style.display = 'inline-block';
    scrapeSelectedBtn.style.display = 'inline-block';
    
    // 存储文件数据用于后续操作
    window.fileListData = files;
    
    let html = '';
    files.forEach((file, index) => {
        const codeClass = file.detected_code ? 'success' : 'warning';
        const codeText = file.detected_code || '未识别';
        const fileId = `file-${index}`;
        
        html += `
            <tr id="${fileId}" data-index="${index}">
                <td>
                    <input type="checkbox" class="form-check-input file-checkbox" 
                           data-index="${index}" onchange="updateSelectedCount()">
                </td>
                <td>
                    <div class="file-name-container">
                        <span class="file-name-display" id="name-${index}">${file.filename}</span>
                        <input type="text" class="form-control form-control-sm rename-input" 
                               id="rename-${index}" value="${file.filename}"
                               onkeypress="handleRenameKeypress(event, ${index})"
                               onblur="handleRenameBlur(event, ${index})">
                    </div>
                    <small class="text-muted">${file.path}</small>
                </td>
                <td>${file.size_mb} MB</td>
                <td>
                    <span class="badge bg-${codeClass}">${codeText}</span>
                </td>
                <td>
                    <div class="file-actions">
                        <button class="btn btn-sm btn-outline-primary" onclick="renameFile(${index})" 
                                title="重命名" id="rename-btn-${index}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteFile(${index})" 
                                title="删除">
                            <i class="bi bi-trash"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success" onclick="scrapeFile(${index})" 
                                title="刮削" id="scrape-btn-${index}">
                            <i class="bi bi-play-circle"></i> 刮削
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
}

// 刮削单个文件
async function scrapeFile(index) {
    const file = window.fileListData[index];
    const scrapeBtn = document.getElementById(`scrape-btn-${index}`);
    
    try {
        // 更新按钮状态
        scrapeBtn.disabled = true;
        scrapeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>刮削中...';
        
        const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: file.path,
                code: file.detected_code || null
            })
        });
        
        const result = await response.json();
        
        // 打印响应结果以便调试
        console.log('刮削响应:', result);
        
        if (result.success) {
            // 检查是否有文件组织信息
            if (result.data && result.data.target_path) {
                showToast(`文件 ${file.filename} 刮削成功，已移动到: ${result.data.target_path}`, 'success');
                console.log(`文件已移动到: ${result.data.target_path}`);
                // 立即刷新历史记录
                if (typeof loadHistory === 'function') {
                    loadHistory();
                }
            } else if (result.metadata) {
                showToast(`文件 ${file.filename} 刮削成功，已获取元数据`, 'success');
                console.log('已获取元数据:', result.metadata);
            } else {
                showToast(`文件 ${file.filename} 刮削成功`, 'success');
            }
            
            // 更新行显示
            const row = document.getElementById(`file-${index}`);
            row.classList.add('table-success');
            setTimeout(() => {
                row.classList.remove('table-success');
                // 刷新文件列表，因为文件可能已被移动
                scanFiles();
            }, 2000);
        } else {
            // 检查失败原因
            if (result.details && result.details.reason === 'invalid_actress') {
                console.warn('无效女优信息:', result.details.actresses);
                showToast(`文件 ${file.filename} 保留在原位：无有效女优信息`, 'warning');
                // 更新行显示为警告状态
                const row = document.getElementById(`file-${index}`);
                row.classList.add('table-warning');
                setTimeout(() => {
                    row.classList.remove('table-warning');
                }, 3000);
            } else {
                console.error('刮削失败:', result.error || result.message);
                showToast(`刮削失败: ${result.error || result.message}`, 'danger');
            }
            // 检查是否有历史记录更新（即使失败也会记录）
            if (typeof loadHistory === 'function') {
                loadHistory();
            }
        }
        
    } catch (error) {
        console.error('刮削失败:', error);
        showToast('刮削失败', 'danger');
    } finally {
        scrapeBtn.disabled = false;
        scrapeBtn.innerHTML = '<i class="bi bi-play-circle"></i> 刮削';
    }
}

// 批量刮削选中的文件
async function scrapeSelectedFiles() {
    const selectedFiles = [];
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    
    checkboxes.forEach(checkbox => {
        const index = parseInt(checkbox.dataset.index);
        selectedFiles.push(window.fileListData[index]);
    });
    
    if (selectedFiles.length === 0) {
        showToast('请选择要刮削的文件', 'warning');
        return;
    }
    
    const scrapeBtn = document.getElementById('scrape-selected-btn');
    scrapeBtn.disabled = true;
    scrapeBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>刮削中 (0/${selectedFiles.length})`;
    
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        scrapeBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>刮削中 (${i}/${selectedFiles.length})`;
        
        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_path: file.path,
                    code: file.detected_code || null
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                successCount++;
            } else {
                failCount++;
                console.error(`刮削失败 ${file.filename}: ${result.error}`);
            }
            
        } catch (error) {
            failCount++;
            console.error(`刮削失败 ${file.filename}:`, error);
        }
    }
    
    scrapeBtn.disabled = false;
    scrapeBtn.innerHTML = '<i class="bi bi-collection-play"></i> 批量刮削';
    
    showToast(`批量刮削完成: 成功 ${successCount} 个, 失败 ${failCount} 个`, 
              failCount > 0 ? 'warning' : 'success');
    
    // 刷新文件列表和历史记录
    setTimeout(() => {
        scanFiles();
        if (typeof loadHistory === 'function') {
            loadHistory();
        }
    }, 1000);
}

// 切换实时监控
function toggleMonitoring() {
    const monitorBtn = document.getElementById('monitor-btn');
    
    if (monitoringEnabled) {
        // 停止监控
        monitoringEnabled = false;
        if (monitoringInterval) {
            clearInterval(monitoringInterval);
            monitoringInterval = null;
        }
        monitorBtn.innerHTML = '<i class="bi bi-eye"></i> 实时监控';
        monitorBtn.classList.remove('btn-warning');
        monitorBtn.classList.add('btn-secondary');
        showToast('已停止实时监控', 'info');
    } else {
        // 开始监控
        monitoringEnabled = true;
        monitorBtn.innerHTML = '<i class="bi bi-eye-slash"></i> 停止监控';
        monitorBtn.classList.remove('btn-secondary');
        monitorBtn.classList.add('btn-warning');
        
        // 立即扫描一次
        scanFiles();
        
        // 设置定时扫描（每5秒）
        monitoringInterval = setInterval(() => {
            if (monitoringEnabled) {
                scanFiles();
            }
        }, 5000);
        
        showToast('已开启实时监控，每5秒自动刷新', 'success');
    }
}

// 更新选中数量
function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const scrapeBtn = document.getElementById('scrape-selected-btn');
    
    if (checkboxes.length > 0) {
        deleteBtn.disabled = false;
        scrapeBtn.disabled = false;
        deleteBtn.innerHTML = `<i class="bi bi-trash"></i> 删除选中 (${checkboxes.length})`;
        scrapeBtn.innerHTML = `<i class="bi bi-collection-play"></i> 批量刮削 (${checkboxes.length})`;
    } else {
        deleteBtn.disabled = true;
        scrapeBtn.disabled = true;
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i> 删除选中';
        scrapeBtn.innerHTML = '<i class="bi bi-collection-play"></i> 批量刮削';
    }
}

// 开始任务 (已废弃，保留以防旧代码调用)
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

// 检查任务状态 (已废弃)
async function checkTaskStatus() {
    return; // 任务管理页面已移除
    
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
loadStats = async function() {
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

// ========== 文件管理功能 ==========

// 全选/取消全选
function selectAllFiles(checkbox) {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
        const row = cb.closest('tr');
        if (checkbox.checked) {
            row.classList.add('selected');
        } else {
            row.classList.remove('selected');
        }
    });
    updateSelectedCount();
}

// 切换全选状态
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    selectAllCheckbox.checked = !selectAllCheckbox.checked;
    selectAllFiles(selectAllCheckbox);
}

// 更新选中数量
function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const allCheckboxes = document.querySelectorAll('.file-checkbox');
    
    // 更新删除按钮状态
    deleteBtn.disabled = checkboxes.length === 0;
    
    // 更新按钮文本
    if (checkboxes.length > 0) {
        deleteBtn.innerHTML = `<i class="bi bi-trash"></i> 删除选中 (${checkboxes.length})`;
    } else {
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i> 删除选中';
    }
    
    // 更新行的选中状态
    allCheckboxes.forEach(cb => {
        const row = cb.closest('tr');
        if (cb.checked) {
            row.classList.add('selected');
        } else {
            row.classList.remove('selected');
        }
    });
    
    // 更新全选框状态
    if (allCheckboxes.length > 0) {
        selectAllCheckbox.checked = checkboxes.length === allCheckboxes.length;
        selectAllCheckbox.indeterminate = checkboxes.length > 0 && checkboxes.length < allCheckboxes.length;
    }
}

// 用于跟踪是否正在保存重命名
let isRenamingSaving = false;

// 重命名文件
function renameFile(index) {
    console.log('renameFile called with index:', index);
    const nameDisplay = document.getElementById(`name-${index}`);
    const renameInput = document.getElementById(`rename-${index}`);
    const renameBtn = document.getElementById(`rename-btn-${index}`);
    
    console.log('Elements found:', {nameDisplay, renameInput, renameBtn});
    console.log('Input has active class:', renameInput?.classList.contains('active'));
    
    if (renameInput.classList.contains('active')) {
        // 保存重命名
        console.log('Saving rename...');
        isRenamingSaving = true;
        saveRename(index);
    } else {
        // 进入编辑模式
        console.log('Entering edit mode...');
        nameDisplay.classList.add('editing');
        renameInput.classList.add('active');
        renameInput.focus();
        renameInput.select();
        renameBtn.innerHTML = '<i class="bi bi-check"></i>';
        
        // 设置当前编辑的索引
        renameInput.dataset.editing = 'true';
    }
}

// 处理重命名键盘事件
function handleRenameKeypress(event, index) {
    if (event.key === 'Enter') {
        event.preventDefault();
        isRenamingSaving = true;
        saveRename(index);
    } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelRename(index);
    }
}

// 处理重命名输入框失焦
function handleRenameBlur(event, index) {
    // 延迟执行，让点击事件先触发
    setTimeout(() => {
        if (!isRenamingSaving) {
            cancelRename(index);
        }
        isRenamingSaving = false;
    }, 200);
}

// 保存重命名
async function saveRename(index) {
    const file = window.fileListData[index];
    const renameInput = document.getElementById(`rename-${index}`);
    const newName = renameInput.value.trim();
    
    if (!newName || newName === file.filename) {
        cancelRename(index);
        return;
    }
    
    try {
        const response = await fetch('/api/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                old_path: file.path,
                new_name: newName
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 更新文件数据
            const oldFilename = file.filename;
            file.filename = newName;
            // 更新文件路径
            file.path = file.path.replace(oldFilename, newName);
            
            const nameDisplay = document.getElementById(`name-${index}`);
            nameDisplay.textContent = newName;
            
            // 更新表格中显示的路径
            const pathDisplay = renameInput.closest('td').querySelector('small.text-muted');
            if (pathDisplay) {
                pathDisplay.textContent = file.path;
            }
            
            showToast(`文件重命名成功`, 'success');
            cancelRename(index);
            isRenamingSaving = false;
        } else {
            showToast(`重命名失败: ${result.error}`, 'danger');
            isRenamingSaving = false;
        }
    } catch (error) {
        console.error('重命名失败:', error);
        showToast('重命名失败', 'danger');
        isRenamingSaving = false;
        cancelRename(index);
    }
}

// 取消重命名
function cancelRename(index) {
    const nameDisplay = document.getElementById(`name-${index}`);
    const renameInput = document.getElementById(`rename-${index}`);
    const renameBtn = document.getElementById(`rename-btn-${index}`);
    const file = window.fileListData[index];
    
    nameDisplay.classList.remove('editing');
    renameInput.classList.remove('active');
    renameInput.value = file.filename;
    renameBtn.innerHTML = '<i class="bi bi-pencil"></i>';
    renameInput.dataset.editing = 'false';
    isRenamingSaving = false;
}

// 删除单个文件
async function deleteFile(index) {
    const file = window.fileListData[index];
    
    if (!confirm(`确定要删除文件 "${file.filename}" 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                paths: [file.path]
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 从列表中移除
            document.getElementById(`file-${index}`).remove();
            window.fileListData.splice(index, 1);
            
            showToast('文件删除成功', 'success');
            
            // 如果没有文件了，显示空状态
            if (window.fileListData.length === 0) {
                document.getElementById('file-list-table').style.display = 'none';
                document.getElementById('empty-state').style.display = 'block';
                document.getElementById('select-all-btn').style.display = 'none';
                document.getElementById('delete-selected-btn').style.display = 'none';
            }
        } else {
            showToast(`删除失败: ${result.error}`, 'danger');
        }
    } catch (error) {
        console.error('删除失败:', error);
        showToast('删除失败', 'danger');
    }
}

// 批量删除选中的文件
async function deleteSelectedFiles() {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    
    if (checkboxes.length === 0) {
        showToast('请先选择要删除的文件', 'warning');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${checkboxes.length} 个文件吗？`)) {
        return;
    }
    
    const paths = [];
    const indices = [];
    
    checkboxes.forEach(cb => {
        const index = parseInt(cb.dataset.index);
        const file = window.fileListData[index];
        paths.push(file.path);
        indices.push(index);
    });
    
    try {
        const response = await fetch('/api/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                paths: paths
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 从大到小排序索引，这样删除时不会影响其他索引
            indices.sort((a, b) => b - a);
            
            // 删除元素和数据
            indices.forEach(index => {
                document.getElementById(`file-${index}`).remove();
                window.fileListData.splice(index, 1);
            });
            
            showToast(`成功删除 ${checkboxes.length} 个文件`, 'success');
            
            // 重新扫描以刷新列表
            scanFiles();
        } else {
            showToast(`批量删除失败: ${result.error}`, 'danger');
        }
    } catch (error) {
        console.error('批量删除失败:', error);
        showToast('批量删除失败', 'danger');
    }
}

// 处理单个文件
async function processFile(index) {
    const file = window.fileListData[index];
    
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                files: [{
                    path: file.path,
                    filename: file.filename,
                    detected_code: file.detected_code,
                    size: file.size_mb * 1024 * 1024
                }]
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`文件 "${file.filename}" 处理成功`, 'success');
            
            // 如果文件被移动了，从列表中移除
            if (result.results && result.results[0] && result.results[0].success) {
                document.getElementById(`file-${index}`).remove();
                window.fileListData.splice(index, 1);
            }
        } else {
            showToast(`处理失败: ${result.error}`, 'danger');
        }
    } catch (error) {
        console.error('处理文件失败:', error);
        showToast('处理文件失败', 'danger');
    }
}

// ==================== JavDB登录相关功能 ====================

// 检查Cookie状态
async function checkCookieStatus() {
    try {
        const response = await fetch('/api/javdb/cookie-status');
        const result = await response.json();
        
        if (result.success && result.status) {
            const status = result.status;
            const statusCard = document.getElementById('cookie-status-card');
            const statusText = document.getElementById('cookie-status-text');
            const cookieDetails = document.getElementById('cookie-details');
            
            if (status.exists) {
                if (status.valid) {
                    statusCard.className = 'card border-success';
                    statusText.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i> Cookies有效';
                    statusText.className = 'card-text mb-0 text-success';
                } else {
                    statusCard.className = 'card border-warning';
                    statusText.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-warning"></i> Cookies可能已过期';
                    statusText.className = 'card-text mb-0 text-warning';
                }
                
                // 显示详细信息
                if (status.timestamp) {
                    document.getElementById('cookie-timestamp').textContent = new Date(status.timestamp).toLocaleString();
                }
                if (status.cookie_count !== undefined) {
                    document.getElementById('cookie-count').textContent = status.cookie_count;
                }
                if (status.age_days !== undefined) {
                    document.getElementById('cookie-age').textContent = `${status.age_days} 天`;
                }
                cookieDetails.style.display = 'block';
            } else {
                statusCard.className = 'card border-secondary';
                statusText.innerHTML = '<i class="bi bi-x-circle text-secondary"></i> 未找到保存的Cookies';
                statusText.className = 'card-text mb-0 text-secondary';
                cookieDetails.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('获取Cookie状态失败:', error);
        showToast('获取Cookie状态失败', 'danger');
    }
}

// 执行JavDB登录 - 提供多种登录方式
async function performJavDBLogin() {
    console.log('开始JavDB登录...');
    const loginBtn = document.getElementById('login-btn');
    
    // 创建登录选项弹窗
    const loginOptions = `
        <div class="modal fade" id="javdbLoginModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">JavDB 登录</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="login-options">
                            <div class="alert alert-info">
                                <strong>提示：</strong>JavDB 需要通过代理访问。请先配置代理，然后选择登录方式。
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-body">
                                            <h5 class="card-title">
                                                <i class="bi bi-window"></i> 浏览器窗口登录
                                            </h5>
                                            <p class="card-text text-muted">
                                                打开浏览器窗口，您可以手动登录，系统会自动保存Cookies
                                            </p>
                                            <button class="btn btn-primary" onclick="openBrowserLogin()">
                                                <i class="bi bi-box-arrow-up-right"></i> 打开浏览器
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <div class="card">
                                        <div class="card-body">
                                            <h5 class="card-title">
                                                <i class="bi bi-key"></i> 账号密码登录
                                            </h5>
                                            <p class="card-text text-muted">
                                                输入账号密码和验证码进行登录（需要手动输入验证码）
                                            </p>
                                            <button class="btn btn-secondary" onclick="showManualLogin()">
                                                <i class="bi bi-person-circle"></i> 手动登录
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-3">
                                <div class="card border-warning">
                                    <div class="card-body">
                                        <h6 class="card-title text-warning">
                                            <i class="bi bi-exclamation-triangle"></i> 配置代理
                                        </h6>
                                        <p class="card-text small">
                                            如果无法访问JavDB，请先配置代理：
                                        </p>
                                        <pre class="bg-light p-2 small">docker exec -it av-metadata-scraper vi /app/config/config.yaml

# 添加以下配置：
network:
  proxy_url: "http://your-proxy:port"</pre>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="browser-login-status" style="display: none;">
                            <div class="text-center">
                                <div class="spinner-border text-primary mb-3" role="status">
                                    <span class="visually-hidden">等待登录...</span>
                                </div>
                                <h5>浏览器窗口已打开</h5>
                                <p>请在打开的浏览器窗口中完成JavDB登录</p>
                                <p class="text-muted">登录成功后，系统会自动保存Cookies并关闭窗口</p>
                                <div class="mt-3">
                                    <button class="btn btn-secondary" onclick="checkBrowserLoginStatus()">
                                        <i class="bi bi-arrow-clockwise"></i> 检查状态
                                    </button>
                                    <button class="btn btn-danger" onclick="closeBrowserLogin()">
                                        <i class="bi bi-x-circle"></i> 关闭窗口
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <div id="manual-login-form" style="display: none;">
                            <!-- 手动登录表单内容会在showManualLogin()中添加 -->
                        <h5 class="modal-title">JavDB 登录</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="login-step-1">
                            <div class="mb-3">
                                <label class="form-label">用户名</label>
                                <input type="text" class="form-control" id="javdb-username" placeholder="请输入JavDB用户名">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">密码</label>
                                <input type="password" class="form-control" id="javdb-password" placeholder="请输入密码">
                            </div>
                            <button class="btn btn-primary" onclick="getJavDBCaptcha()">
                                <i class="bi bi-arrow-right"></i> 获取验证码
                            </button>
                        </div>
                        
                        <div id="login-step-2" style="display: none;">
                            <div class="alert alert-info">
                                <strong>提示：</strong>如果看不到验证码，说明JavDB无法访问，请配置代理。
                            </div>
                            <div class="text-center mb-3">
                                <img id="captcha-image" src="" alt="验证码" style="max-width: 300px; border: 1px solid #ddd; padding: 10px;">
                                <br>
                                <button class="btn btn-sm btn-secondary mt-2" onclick="getJavDBCaptcha()">
                                    <i class="bi bi-arrow-clockwise"></i> 刷新验证码
                                </button>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">验证码</label>
                                <input type="text" class="form-control" id="javdb-captcha" placeholder="请输入上图中的验证码">
                            </div>
                            <button class="btn btn-success" onclick="submitJavDBLogin()">
                                <i class="bi bi-check-circle"></i> 提交登录
                            </button>
                        </div>
                        
                        <div id="login-loading" style="display: none;">
                            <div class="text-center">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">加载中...</span>
                                </div>
                                <p class="mt-3">正在处理...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 添加模态框到页面（如果不存在）
    if (!document.getElementById('javdbLoginModal')) {
        document.body.insertAdjacentHTML('beforeend', loginForm);
    }
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('javdbLoginModal'));
    modal.show();
}

// 获取验证码
async function getJavDBCaptcha() {
    const username = document.getElementById('javdb-username').value;
    const password = document.getElementById('javdb-password').value;
    
    if (!username || !password) {
        showToast('请先输入用户名和密码', 'warning');
        return;
    }
    
    // 显示加载状态
    document.getElementById('login-step-1').style.display = 'none';
    document.getElementById('login-loading').style.display = 'block';
    
    try {
        const response = await fetch('/api/javdb/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                method: 'semi_auto',
                action: 'get_captcha'
            })
        });
        
        console.log('响应状态:', response.status);
        const result = await response.json();
        console.log('响应结果:', result);
        
        document.getElementById('login-loading').style.display = 'none';
        
        if (result.success && result.captcha_image) {
            // 显示验证码
            document.getElementById('captcha-image').src = result.captcha_image;
            document.getElementById('login-step-2').style.display = 'block';
            showToast('验证码获取成功，请输入验证码', 'info');
        } else {
            // 获取失败
            document.getElementById('login-step-1').style.display = 'block';
            showToast(result.error || '获取验证码失败，可能需要配置代理', 'danger');
        }
    } catch (error) {
        console.error('获取验证码失败:', error);
        document.getElementById('login-loading').style.display = 'none';
        document.getElementById('login-step-1').style.display = 'block';
        showToast('获取验证码失败', 'danger');
    }
}

// 提交登录
async function submitJavDBLogin() {
    const username = document.getElementById('javdb-username').value;
    const password = document.getElementById('javdb-password').value;
    const captcha = document.getElementById('javdb-captcha').value;
    
    if (!captcha) {
        showToast('请输入验证码', 'warning');
        return;
    }
    
    // 显示加载状态
    document.getElementById('login-step-2').style.display = 'none';
    document.getElementById('login-loading').style.display = 'block';
    
    try {
        const response = await fetch('/api/javdb/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                method: 'semi_auto',
                action: 'submit',
                username: username,
                password: password,
                captcha: captcha
            })
        });
        
        const result = await response.json();
        document.getElementById('login-loading').style.display = 'none';
        
        if (result.success) {
            // 登录成功
            showToast('登录成功！Cookies已保存', 'success');
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('javdbLoginModal'));
            modal.hide();
            // 刷新Cookie状态
            await checkCookieStatus();
        } else if (result.retry && result.new_captcha) {
            // 验证码错误，显示新验证码
            document.getElementById('captcha-image').src = result.new_captcha;
            document.getElementById('javdb-captcha').value = '';
            document.getElementById('login-step-2').style.display = 'block';
            showToast(result.error || '验证码错误，请重新输入', 'warning');
        } else {
            // 其他错误
            document.getElementById('login-step-1').style.display = 'block';
            showToast(result.error || '登录失败', 'danger');
        }
    } catch (error) {
        console.error('提交登录失败:', error);
        document.getElementById('login-loading').style.display = 'none';
        document.getElementById('login-step-1').style.display = 'block';
        showToast('提交登录失败', 'danger');
    }
}

// 验证Cookies
async function verifyCookies() {
    const verifyBtn = document.getElementById('verify-btn');
    const originalText = verifyBtn.innerHTML;
    
    try {
        // 显示加载状态
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>验证中...';
        
        const response = await fetch('/api/javdb/verify-cookies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.valid) {
                showToast('Cookies验证成功，可以正常使用', 'success');
            } else {
                showToast('Cookies无效或已过期，请重新登录', 'warning');
            }
            // 刷新状态
            await checkCookieStatus();
        } else {
            showToast('验证失败: ' + result.error, 'danger');
        }
        
    } catch (error) {
        console.error('验证失败:', error);
        showToast('验证请求失败', 'danger');
    } finally {
        // 恢复按钮状态
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = originalText;
    }
}

// 清除Cookies
async function clearCookies() {
    if (!confirm('确定要清除所有保存的JavDB Cookies吗？清除后需要重新登录。')) {
        return;
    }
    
    const clearBtn = document.getElementById('clear-btn');
    const originalText = clearBtn.innerHTML;
    
    try {
        // 显示加载状态
        clearBtn.disabled = true;
        clearBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>清除中...';
        
        const response = await fetch('/api/javdb/clear-cookies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Cookies已清除', 'success');
            // 刷新状态
            await checkCookieStatus();
        } else {
            showToast('清除失败: ' + result.error, 'danger');
        }
        
    } catch (error) {
        console.error('清除失败:', error);
        showToast('清除请求失败', 'danger');
    } finally {
        // 恢复按钮状态
        clearBtn.disabled = false;
        clearBtn.innerHTML = originalText;
    }
}

// 复制到剪贴板
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板', 'success');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败，请手动复制', 'warning');
    });
}

// 当切换到JavDB页面时，自动检查Cookie状态
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-link[data-page="javdb"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            setTimeout(() => {
                checkCookieStatus();
            }, 100);
        });
    });

// ==================== 历史记录管理 ====================

let historyData = [];
let currentHistoryPage = 1;
const historyPageSize = 20;

// 加载历史记录
loadHistory = async function(search = '', status = '') {
    try {
        let url = '/api/history?limit=1000';
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }
        if (status) {
            url += `&status=${status}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            historyData = data.data || data.entries || [];
            displayHistory();
            updateHistoryStats();
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
        showToast('加载历史记录失败', 'error');
    }
}

// 显示历史记录
function displayHistory() {
    const tbody = document.getElementById('history-tbody');
    if (!tbody) return;
    
    // 计算分页
    const startIndex = (currentHistoryPage - 1) * historyPageSize;
    const endIndex = startIndex + historyPageSize;
    const pageData = historyData.slice(startIndex, endIndex);
    
    if (pageData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">暂无记录</td></tr>';
        return;
    }
    
    tbody.innerHTML = pageData.map(entry => {
        const statusBadge = getStatusBadge(entry.status);
        const processTime = new Date(entry.process_time).toLocaleString('zh-CN');
        const actresses = entry.actresses ? entry.actresses.slice(0, 3).join(', ') : '';
        
        return `
            <tr>
                <td>${processTime}</td>
                <td>${statusBadge}</td>
                <td title="${entry.original_path}">${entry.original_filename}</td>
                <td>${entry.detected_code || '-'}</td>
                <td title="${entry.organized_path || entry.new_path || ''}">${entry.new_filename || '-'}</td>
                <td>${entry.title || '-'}</td>
                <td>${actresses || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="viewHistoryDetail('${btoa(unescape(encodeURIComponent(JSON.stringify(entry))))}')">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // 更新分页控件
    updateHistoryPagination();
}

// 获取状态徽章
function getStatusBadge(status) {
    const badges = {
        'success': '<span class="badge bg-success">成功</span>',
        'failed': '<span class="badge bg-danger">失败</span>',
        'partial': '<span class="badge bg-warning">部分</span>',
        'skipped': '<span class="badge bg-secondary">跳过</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">未知</span>';
}

// 更新历史统计
async function updateHistoryStats() {
    try {
        const response = await fetch('/api/history/stats');
        const data = await response.json();
        
        if (data.success && (data.data || data.stats)) {
            const stats = data.data || data.stats;
            document.getElementById('history-total').textContent = stats.total_processed || 0;
            document.getElementById('history-success').textContent = stats.successful || 0;
            document.getElementById('history-failed').textContent = stats.failed || 0;
            document.getElementById('history-success-rate').textContent = 
                `${(stats.success_rate || 0).toFixed(1)}%`;
        }
    } catch (error) {
        console.error('获取历史统计失败:', error);
    }
}

// 更新分页控件
function updateHistoryPagination() {
    const totalPages = Math.ceil(historyData.length / historyPageSize);
    const pagination = document.getElementById('history-pagination');
    if (!pagination) return;
    
    let html = '';
    
    // 上一页
    html += `
        <li class="page-item ${currentHistoryPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changeHistoryPage(${currentHistoryPage - 1}); return false;">
                上一页
            </a>
        </li>
    `;
    
    // 页码
    for (let i = 1; i <= Math.min(totalPages, 10); i++) {
        html += `
            <li class="page-item ${i === currentHistoryPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changeHistoryPage(${i}); return false;">
                    ${i}
                </a>
            </li>
        `;
    }
    
    // 下一页
    html += `
        <li class="page-item ${currentHistoryPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changeHistoryPage(${currentHistoryPage + 1}); return false;">
                下一页
            </a>
        </li>
    `;
    
    pagination.innerHTML = html;
}

// 切换页面
function changeHistoryPage(page) {
    const totalPages = Math.ceil(historyData.length / historyPageSize);
    if (page < 1 || page > totalPages) return;
    
    currentHistoryPage = page;
    displayHistory();
}

// 搜索历史
searchHistory = function() {
    const searchInput = document.getElementById('history-search');
    const search = searchInput ? searchInput.value : '';
    const filterSelect = document.getElementById('history-filter');
    const status = filterSelect ? filterSelect.value : '';
    
    currentHistoryPage = 1;
    loadHistory(search, status);
}

// 筛选历史
filterHistory = function() {
    searchHistory();
}

// 刷新历史
refreshHistory = function() {
    currentHistoryPage = 1;
    loadHistory();
    showToast('历史记录已刷新', 'success');
}

// 确保函数在全局作用域可用
window.refreshHistory = refreshHistory;
window.searchHistory = searchHistory;
window.exportHistory = exportHistory;
window.clearHistory = clearHistory;
window.filterHistory = filterHistory;
window.loadHistory = loadHistory;
window.viewHistoryDetail = viewHistoryDetail;

// 清空历史
clearHistory = async function() {
    if (!confirm('确定要清空所有历史记录吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        const response = await fetch('/api/history/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days: 0 })  // days=0 表示清空所有记录
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message || '历史记录已清空', 'success');
            loadHistory();
        } else {
            showToast('清空失败: ' + result.error, 'danger');
        }
    } catch (error) {
        console.error('清空历史失败:', error);
        showToast('清空历史失败', 'danger');
    }
}

// 导出历史
exportHistory = async function() {
    try {
        window.location.href = '/api/history/export';
        showToast('开始导出历史记录', 'success');
    } catch (error) {
        console.error('导出失败:', error);
        showToast('导出失败', 'error');
    }
}

// 查看详情
viewHistoryDetail = function(encodedData) {
    try {
        const entry = JSON.parse(decodeURIComponent(escape(atob(encodedData))));
        
        let detailHtml = `
            <div class="modal fade" id="historyDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">处理详情</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <table class="table">
                                <tr><td width="30%"><strong>原始文件名:</strong></td><td>${entry.original_filename}</td></tr>
                                <tr><td><strong>原始路径:</strong></td><td>${entry.original_path}</td></tr>
                                <tr><td><strong>文件大小:</strong></td><td>${(entry.file_size_mb || 0).toFixed(2)} MB</td></tr>
                                <tr><td><strong>处理时间:</strong></td><td>${new Date(entry.process_time).toLocaleString('zh-CN')}</td></tr>
                                <tr><td><strong>处理状态:</strong></td><td>${getStatusBadge(entry.status)}</td></tr>
                                <tr><td><strong>识别代码:</strong></td><td>${entry.detected_code || '-'}</td></tr>
                                <tr><td><strong>新文件名:</strong></td><td>${entry.new_filename || '-'}</td></tr>
                                <tr><td><strong>整理后路径:</strong></td><td>${
                                    // 如果organized_path和original_path相同，说明文件没有被整理
                                    (entry.organized_path && entry.organized_path !== entry.original_path) 
                                        ? entry.organized_path 
                                        : (entry.new_path && entry.new_path !== entry.original_path) 
                                            ? entry.new_path 
                                            : '<span class="text-muted">未整理（保留在源目录）</span>'
                                }</td></tr>
                                <tr><td><strong>标题:</strong></td><td>${entry.title || '-'}</td></tr>
                                <tr><td><strong>演员:</strong></td><td>${entry.actresses ? entry.actresses.join(', ') : '-'}</td></tr>
                                <tr><td><strong>制作商:</strong></td><td>${entry.studio || '-'}</td></tr>
                                <tr><td><strong>发行日期:</strong></td><td>${entry.release_date || '-'}</td></tr>
                                <tr><td><strong>类别:</strong></td><td>${entry.genres ? entry.genres.join(', ') : '-'}</td></tr>
                                ${entry.error_message ? `<tr><td><strong>错误信息:</strong></td><td class="text-danger">${entry.error_message}</td></tr>` : ''}
                            </table>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 移除旧的模态框
        const oldModal = document.getElementById('historyDetailModal');
        if (oldModal) {
            oldModal.remove();
        }
        
        // 添加新的模态框
        document.body.insertAdjacentHTML('beforeend', detailHtml);
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('historyDetailModal'));
        modal.show();
        
    } catch (error) {
        console.error('显示详情失败:', error);
        showToast('显示详情失败', 'error');
    }
}
});
// JavDB VNC 登录功能

// 启动整个登录流程的模态框
function performJavDBLogin() {
    const modalHTML = `
    <div class="modal fade" id="vncLoginModal" tabindex="-1" aria-labelledby="vncLoginModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="vncLoginModalLabel">JavDB VNC 登录</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div id="vnc-login-initial-view">
                        <p>此方法将在服务器上启动一个带图形界面的浏览器，您可以通过VNC（远程桌面）连接上去手动登录。</p>
                        <p>这可以解决所有因为网络、验证码等导致的登录失败问题。</p>
                        <button class="btn btn-primary" onclick="startVNCLoginSession()"> <i class="bi bi-display"></i> 启动VNC登录会话</button>
                    </div>
                    <div id="vnc-login-active-view" style="display: none;">
                        <div class="alert alert-info">
                            <h5 class="alert-heading">VNC会话已启动！</h5>
                            <p>请使用VNC客户端连接到以下地址:</p>
                            <hr>
                            <p class="mb-0"><strong>Web浏览器访问 (推荐):</strong> <a id="vnc-web-url" href="#" target="_blank"></a></p>
                            <p class="mb-0"><strong>VNC客户端访问:</strong> <span id="vnc-client-url"></span> (密码: password)</p>
                        </div>
                        <p>连接后，请在浏览器中完成JavDB的登录操作。</p>
                        <hr>
                        <p><strong>登录完成后</strong>，请点击下面的按钮来保存您的登录信息。</p>
                        <button class="btn btn-success" onclick="checkAndSaveCookiesVNC()"> <i class="bi bi-check-circle"></i> 我已登录，检查并保存Cookies</button>
                    </div>
                    <div id="vnc-login-status" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>
    `;

    if (!document.getElementById('vncLoginModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    const vncModal = new bootstrap.Modal(document.getElementById('vncLoginModal'));
    vncModal.show();
}

// 步骤1: 调用后端启动VNC和浏览器
async function startVNCLoginSession() {
    const statusDiv = document.getElementById('vnc-login-status');
    statusDiv.innerHTML = `<div class="spinner-border spinner-border-sm" role="status"></div> 正在启动VNC会话...`;

    try {
        const response = await fetch('/api/javdb/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'start' })
        });
        const result = await response.json();

        if (result.success) {
            statusDiv.innerHTML = '';
            document.getElementById('vnc-login-initial-view').style.display = 'none';
            document.getElementById('vnc-login-active-view').style.display = 'block';
            
            // 使用当前页面的主机名填充URL
            const hostname = window.location.hostname;
            const webVncUrl = `http://${hostname}:6901`;
            const clientVncUrl = `vnc://${hostname}:5901`;

            document.getElementById('vnc-web-url').href = webVncUrl;
            document.getElementById('vnc-web-url').textContent = webVncUrl;
            document.getElementById('vnc-client-url').textContent = clientVncUrl;

        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">启动失败: ${result.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">请求失败: ${error}</div>`;
    }
}

// 步骤2: 用户登录后，调用后端检查并保存Cookies
async function checkAndSaveCookiesVNC() {
    const statusDiv = document.getElementById('vnc-login-status');
    statusDiv.innerHTML = `<div class="spinner-border spinner-border-sm" role="status"></div> 正在检查登录状态并保存Cookies...`;

    try {
        const response = await fetch('/api/javdb/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'check' })
        });
        const result = await response.json();

        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success">${result.message}</div>`;
            showToast('登录成功，Cookies已保存!', 'success');
            setTimeout(() => {
                const vncModal = bootstrap.Modal.getInstance(document.getElementById('vncLoginModal'));
                vncModal.hide();
                // 可以在这里添加刷新主页面Cookie状态的函数调用
            }, 2000);
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">未能保存Cookies: ${result.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">请求失败: ${error}</div>`;
    }
}

// 在主页面上，将原来的登录按钮的onclick事件改为 showVNCLoginModal()
// 例如: document.getElementById('javdb-login-button').onclick = showVNCLoginModal;

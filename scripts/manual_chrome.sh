#!/bin/bash
# 在容器内手动启动一个可见的Chrome浏览器

echo "============================================================"
echo "手动启动Chrome浏览器到VNC显示"
echo "============================================================"

# 在调试容器内执行
docker exec -it selenium-debug bash -c '
export DISPLAY=:99
chromium \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --window-size=1920,1080 \
    --window-position=0,0 \
    --force-device-scale-factor=1 \
    --user-data-dir=/tmp/chrome-profile \
    https://www.google.com &
'

echo ""
echo "✅ Chrome浏览器已在容器内启动"
echo ""
echo "📺 查看浏览器："
echo "  1. 打开: http://localhost:7901"
echo "  2. 密码: secret"
echo ""
echo "如果还是看不到，试试："
echo "  docker restart selenium-debug"
echo "============================================================"
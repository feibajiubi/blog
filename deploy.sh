#!/bin/bash
# ============================================================
# 博客项目 · 腾讯云 Linux 一键部署脚本
# 用法：在腾讯云控制台终端（VNC/SSH）里执行：
#   bash deploy.sh
# 前提：服务器已安装 Python3.8+、MySQL、git
# ============================================================
set -e

# ---------- 1. 配置区（按需修改）----------
PROJECT_DIR="$HOME/blog"              # 项目部署目录
GIT_URL="https://github.com/feibajiubi/blog.git"   # 你的仓库地址
DJANGO_PORT=8000                      # Django 端口（配合 Nginx 反代）

echo "=================== 1/7 安装系统依赖 ==================="
sudo apt-get update -y || sudo yum update -y || true
# Ubuntu/Debian 需要以下包；CentOS 请改用 yum install -y python3-devel gcc
sudo apt-get install -y python3-venv python3-pip git nginx || \
sudo yum install -y python3-devel gcc git nginx || true

echo "=================== 2/7 拉取代码 ==================="
mkdir -p "$PROJECT_DIR"
if [ -d "$PROJECT_DIR/.git" ]; then
  cd "$PROJECT_DIR" && git pull
else
  git clone "$GIT_URL" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

echo "=================== 3/7 创建虚拟环境并安装依赖 ==================="
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-linux.txt

echo "=================== 4/7 创建 .env 配置文件 ==================="
if [ ! -f .env ]; then
  cp .env.example .env
  echo ">> 已生成 .env 模板，请编辑填入真实值："
  echo "   nano $PROJECT_DIR/.env"
  echo "   必须修改：DJANGO_SECRET_KEY / DB_PASSWORD / DJANGO_DEBUG=False / DJANGO_ALLOWED_HOSTS"
  read -p ">> 编辑完成后按回车继续..." x
else
  echo ">> .env 已存在，跳过"
fi

echo "=================== 5/7 数据库迁移 + 静态文件 ==================="
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

echo "=================== 6/7 启动 Gunicorn（Django）=================="
# 用 nohup 后台启动（简单方式）；更推荐用 systemd，见下方注释
pkill -f "gunicorn blog.wsgi" 2>/dev/null || true
sleep 1
nohup venv/bin/gunicorn blog.wsgi:application \
  --bind 127.0.0.1:$DJANGO_PORT \
  --workers 3 \
  --timeout 120 \
  > /tmp/gunicorn.log 2>&1 &
echo ">> Gunicorn 已启动，端口 $DJANGO_PORT（日志: /tmp/gunicorn.log）"

echo "=================== 7/7 配置 Nginx 反向代理 ==================="
# 生成 Nginx 配置（用服务器公网 IP 或域名）
PUBLIC_IP=$(curl -s ifconfig.me || curl -s ip.sb || echo "YOUR_IP")
cat > /tmp/blog_nginx.conf <<EOF
server {
    listen 80;
    server_name $PUBLIC_IP;

    client_max_body_size 20M;

    location /static/ {
        alias $PROJECT_DIR/static_collected/;
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:$DJANGO_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
sudo cp /tmp/blog_nginx.conf /etc/nginx/sites-available/blog 2>/dev/null || \
sudo cp /tmp/blog_nginx.conf /etc/nginx/conf.d/blog.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/blog 2>/dev/null || true
sudo nginx -t && sudo systemctl reload nginx || sudo nginx -s reload || true

echo ""
echo "======================================================"
echo "部署完成！访问： http://$PUBLIC_IP"
echo ""
echo "后续管理："
echo "  - 重启 Django:  pkill -f gunicorn; cd $PROJECT_DIR && source venv/bin/activate && nohup venv/bin/gunicorn blog.wsgi:application --bind 127.0.0.1:$DJANGO_PORT --workers 3 --timeout 120 > /tmp/gunicorn.log 2>&1 &"
echo "  - 修改配置:     nano $PROJECT_DIR/.env"
echo "  - 部署检查:     cd $PROJECT_DIR && source venv/bin/activate && python deploy_check.py"
echo "  - 单元测试:     cd $PROJECT_DIR && source venv/bin/activate && python manage.py test app01"
echo "======================================================"

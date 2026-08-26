# ============================================================
# 博客项目 · 腾讯云 Linux 部署文档
# ============================================================

## 一、部署前准备

在腾讯云控制台确认：
1. 服务器系统：Ubuntu 20.04+ / CentOS 7+ / Debian（本指南以 Ubuntu 为例）
2. 已安装：Python 3.8+、MySQL 8、git
3. 安全组放行端口：**80**（HTTP）、**22**（SSH）

MySQL 建库（在服务器上执行）：
```sql
CREATE DATABASE blog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'blog'@'localhost' IDENTIFIED BY '你的强密码';
GRANT ALL PRIVILEGES ON blog.* TO 'blog'@'localhost';
FLUSH PRIVILEGES;
```

## 二、一键部署

1. 登录腾讯云控制台 → 服务器 → 登录（网页终端 VNC / SSH）
2. 把 `deploy.sh` 的内容粘贴到终端（或用 `nano deploy.sh` 创建后执行）：
```bash
bash deploy.sh
```
脚本会自动：装依赖 → 拉代码 → 建虚拟环境 → 生成 .env → 迁移 → collectstatic → 启动 gunicorn → 配 nginx

3. 脚本中途会暂停让你编辑 `.env`（填入 SECRET_KEY / 数据库密码 / DEBUG=False / 域名）

## 三、用 systemd 托管（推荐，代替脚本里的 nohup）

编辑 `/etc/systemd/system/blog.service`：
```ini
[Unit]
Description=Django Blog (gunicorn)
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/你的用户名/blog
EnvironmentFile=/home/你的用户名/blog/.env
ExecStart=/home/你的用户名/blog/venv/bin/gunicorn blog.wsgi:application \
    --bind 127.0.0.1:8000 --workers 3 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用：
```bash
sudo systemctl daemon-reload
sudo systemctl enable blog
sudo systemctl start blog
sudo systemctl status blog   # 查看状态
journalctl -u blog -f        # 查看日志
```

## 四、更新代码

```bash
cd /home/你的用户名/blog
git pull
source venv/bin/activate
pip install -r requirements-linux.txt   # 如有新依赖
python manage.py migrate                # 如有新迁移
python manage.py collectstatic --noinput
sudo systemctl restart blog             # 重启服务
```

## 五、常见问题

| 问题 | 解决 |
|---|---|
| 502 Bad Gateway | gunicorn 没起来：`journalctl -u blog -f` 看日志 |
| 静态文件 404 | 确认 nginx 的 `/static/` 指向 `static_collected/`，且已 collectstatic |
| 数据库连接失败 | 检查 .env 的 DB_* 配置，确认 MySQL 用户/密码/库名正确 |
| 媒体文件（头像/词云） | nginx 的 `/media/` 指向项目 `media/` 目录，确认目录权限 |
| 中文乱码 | 确保数据库是 utf8mb4，settings 里 OPTIONS charset 已是 utf8mb4 |
| AI 对话不工作 | .env 里配 `DEEPSEEK_API_KEY`，重启服务 |

## 六、安全检查

```bash
cd /home/你的用户名/blog && source venv/bin/activate
python deploy_check.py   # 会检查 DEBUG/密钥/域名 等隐患
```

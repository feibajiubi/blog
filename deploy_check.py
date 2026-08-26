# -*- coding: utf-8 -*-
"""部署安全检查脚本：部署前运行，检查常见生产环境隐患。
用法：python deploy_check.py
"""
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog.settings')
django.setup()

from blog import settings


def check(name, ok, advice):
    status = '[OK]' if ok else '[FAIL]'
    print(f'{status} {name}')
    if not ok:
        print(f'     ! {advice}')


def main():
    print('=' * 50)
    print('部署安全检查')
    print('=' * 50)

    # 1. DEBUG
    check('DEBUG 已关闭 (False)', not settings.DEBUG,
          '生产环境必须 DEBUG=False，否则会泄露报错堆栈和配置信息。'
          '在 .env 中设置 DJANGO_DEBUG=False')

    # 2. SECRET_KEY
    check('SECRET_KEY 来自环境变量', not settings.SECRET_KEY.startswith('django-insecure-'),
          'SECRET_KEY 使用了默认值，请在 .env 中配置 DJANGO_SECRET_KEY')

    # 3. ALLOWED_HOSTS
    hosts_ok = settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != ['*']
    check('ALLOWED_HOSTS 已配置具体域名', hosts_ok,
          'ALLOWED_HOSTS 为通配符 *，生产环境应改为具体域名，'
          '在 .env 中设置 DJANGO_ALLOWED_HOSTS=www.example.com,example.com')

    # 4. 数据库密码
    db_pass = settings.DATABASES['default'].get('PASSWORD', '')
    check('数据库密码来自环境变量', bool(db_pass) and db_pass != '',
          '数据库密码为空，请在 .env 中配置 DB_PASSWORD')

    # 5. DeepSeek Key（可选提醒）
    if settings.DEEPSEEK_API_KEY:
        print('[OK] DEEPSEEK_API_KEY 已配置（AI 对话可用）')
    else:
        print('[INFO]  DEEPSEEK_API_KEY 未配置（AI 对话将降级为规则+RAG）')

    print('=' * 50)
    fails = [
        settings.DEBUG,
        settings.SECRET_KEY.startswith('django-insecure-'),
        not hosts_ok,
    ]
    if any(fails):
        print('[WARN]  发现 {} 项需要修复的隐患，请按上方提示处理后再部署。'.format(sum(fails)))
        sys.exit(1)
    print('[OK] 检查通过，可以安全部署！')


if __name__ == '__main__':
    main()

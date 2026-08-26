# -*- coding: utf-8 -*-
"""核心功能单元测试（登录 / 点赞 / 爬虫清洗 / 分页 / RSS / XSS）"""
import json
import os

from django.test import TestCase, Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog.settings')

from app01 import models
from app01.crawler import sanitize_html


class BaseTest(TestCase):
    """公共测试基类：创建用户/站点/分类/文章"""

    def setUp(self):
        self.user = models.UserInfo.objects.create_user(
            username='testuser', password='testpass123')
        self.blog = models.Blog.objects.create(
            site_name='测试站', site_title='测试站Blog')
        self.user.blog = self.blog
        self.user.save()
        self.category = models.Category.objects.create(name='测试分类')
        self.article = models.Article.objects.create(
            title='测试文章一',
            desc='这是第一篇测试文章',
            content='<p>正文内容</p>',
            blog=self.blog,
            category=self.category,
        )
        self.article2 = models.Article.objects.create(
            title='测试文章二',
            desc='这是第二篇测试文章',
            content='<p>正文内容二</p>',
            blog=self.blog,
            category=self.category,
        )
        self.client = Client()


class LoginTest(BaseTest):
    """登录/注册/权限测试"""

    def test_login_wrong_password(self):
        resp = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'wrongpass',
            'code': 'xxxx',
        })
        data = json.loads(resp.content)
        self.assertEqual(data['code'], 1002)  # 验证码错误

    def test_crawl_requires_login(self):
        resp = self.client.get('/crawl/')
        self.assertEqual(resp.status_code, 302)  # 未登录重定向

    def test_dashboard_public(self):
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)  # 公开可访问


class UpDownTest(BaseTest):
    """点赞/点踩逻辑测试"""

    def test_up_article(self):
        other = models.UserInfo.objects.create_user(username='other', password='x123456')
        other_blog = models.Blog.objects.create(site_name='他人站', site_title='他人')
        other.blog = other_blog
        other.save()
        other_article = models.Article.objects.create(
            title='他人文章', desc='d', content='<p>c</p>',
            blog=other_blog, category=self.category)

        self.client.login(username='testuser', password='testpass123')
        resp = self.client.post('/up_or_down/', {
            'article_id': other_article.id,
            'is_up': 'true',
        })
        data = json.loads(resp.content)
        self.assertEqual(data['code'], 0)
        other_article.refresh_from_db()
        self.assertEqual(other_article.up_num, 1)

    def test_cannot_up_own_article(self):
        self.client.login(username='testuser', password='testpass123')
        resp = self.client.post('/up_or_down/', {
            'article_id': self.article.id,
            'is_up': 'true',
        })
        data = json.loads(resp.content)
        self.assertEqual(data['code'], 1001)  # 不能给自己点赞


class CrawlerTest(BaseTest):
    """爬虫 XSS 清洗测试（不依赖网络）"""

    def test_sanitize_removes_script(self):
        out = sanitize_html('<p>hi<script>alert(1)</script></p>')
        self.assertNotIn('<script', out)

    def test_sanitize_removes_event_attrs(self):
        out = sanitize_html('<p onclick="alert(1)">x</p><img src="x" onerror="alert(2)">')
        self.assertNotIn('onclick', out)
        self.assertNotIn('onerror', out)

    def test_sanitize_blocks_javascript_url(self):
        out = sanitize_html('<a href="javascript:alert(1)">bad</a>')
        self.assertNotIn('javascript:', out)

    def test_sanitize_keeps_code_block(self):
        out = sanitize_html('<pre><code>print(1)</code></pre>')
        self.assertIn('<pre>', out)
        self.assertIn('print(1)', out)


class PaginationTest(BaseTest):
    """分页测试"""

    def test_home_page_12_per_page(self):
        # 创建 13 篇额外文章（共 15 篇 → 第 1 页 12 篇）
        for i in range(13):
            models.Article.objects.create(
                title=f'批量文章{i}', desc='d', content='<p>c</p>',
                blog=self.blog, category=self.category)
        resp = self.client.get('/home/')
        html = resp.content.decode('utf-8')
        self.assertEqual(html.count('media-heading'), 12)  # 每页12篇

    def test_page_2_works(self):
        resp = self.client.get('/home/?page=2')
        self.assertEqual(resp.status_code, 200)


class RssTest(BaseTest):
    """RSS 订阅测试"""

    def test_rss_feed(self):
        resp = self.client.get('/rss/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/rss', resp['Content-Type'])
        html = resp.content.decode('utf-8')
        self.assertIn('<rss', html)
        self.assertIn('测试文章一', html)


class StatsTest(BaseTest):
    """宠物接口测试"""

    def test_pet_stats(self):
        resp = self.client.get('/pet/stats/')
        data = json.loads(resp.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['stats']['total'], 2)

    def test_article_stats(self):
        resp = self.client.get(f'/pet/stats/?article={self.article.id}')
        data = json.loads(resp.content)
        self.assertEqual(data['article_stats']['title'], '测试文章一')

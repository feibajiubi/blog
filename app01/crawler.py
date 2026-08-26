# -*- coding: utf-8 -*-
"""博客园(cnblogs.com)文章爬虫模块
职责：爬取列表页 → 解析候选文章 → 抓取详情正文 → 清洗HTML → 去重
供 /crawl/ 系列视图调用。
"""
import re
import requests
from bs4 import BeautifulSoup

# 通用请求头（模拟浏览器，降低被拒绝概率）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
TIMEOUT = 10          # 请求超时（秒）
MAX_CONTENT_LEN = 50000  # 正文最多保留字符数（防止大页面卡死）

# 清洗时要移除的标签（无意义/干扰元素）
REMOVE_SELECTORS = ['script', 'style', 'nav', 'header', 'footer', 'aside',
                    'iframe', 'form', 'button', 'input', '.adsbygoogle',
                    '.blog_comment', '#comment_form', '.post_desc']


def _get(url):
    """带超时和异常的 GET 请求；失败抛异常由调用方处理"""
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or 'utf-8'
    return resp


def fetch_article_list(url):
    """爬取博客园列表页，返回候选文章列表：
    [{title, url, summary, author, pub_time}]
    """
    resp = _get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    items = soup.select('.post-item') or soup.select('.post_item')
    results = []
    for it in items:
        title_el = it.select_one('.post-item-title') or it.select_one('.titlelnk') or it.select_one('a')
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = title_el.get('href')
        if not title or not href:
            continue
        # 摘要
        sum_el = it.select_one('.post-item-summary')
        summary = sum_el.get_text(' ', strip=True)[:255] if sum_el else ''
        # 底部信息：作者 + 时间（如 "yuyuyui 2026-08-26 19:52 0 0 13"）
        author = ''
        pub_time = ''
        foot_el = it.select_one('.post-item-foot')
        if foot_el:
            foot_text = foot_el.get_text(' ', strip=True)
            m = re.match(r'([\w\u4e00-\u9fa5\-\.]+)\s+(\d{4}-\d{2}-\d{2})', foot_text)
            if m:
                author = m.group(1)
                pub_time = m.group(2)
        results.append({
            'title': title,
            'url': href,
            'summary': summary,
            'author': author,
            'pub_time': pub_time,
        })
    return results


def fetch_article_detail(url):
    """爬取单篇文章详情，返回 {title, content_html, content_text}；
    正文 HTML 已清洗（去 script/style/nav 等，保留 pre/code 代码块）。
    """
    resp = _get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    title_el = soup.select_one('#cb_post_title_url') or soup.select_one('h1.postTitle') or soup.select_one('h1')
    title = title_el.get_text(strip=True) if title_el else ''

    body = (soup.select_one('#cnblogs_post_body')
            or soup.select_one('.postBody')
            or soup.select_one('#blog_post_body'))
    if not body:
        return {'title': title, 'content_html': '', 'content_text': ''}

    # 复制一份避免影响原 soup
    body = BeautifulSoup(str(body), 'html.parser')

    # 1. 移除干扰标签
    for sel in REMOVE_SELECTORS:
        for tag in body.select(sel):
            tag.decompose()
    # 2. 移除 a 标签但保留文字（避免外链跳转）
    for a in body.select('a'):
        a.replace_with(a.get_text())
    # 3. 移除属性（class/style/id 等），只保留结构标签与 href 类安全属性
    for tag in body.find_all(True):
        for attr in list(tag.attrs):
            if attr not in ('href', 'src', 'alt', 'colspan', 'rowspan'):
                del tag.attrs[attr]

    # 截断超长正文，避免导入超大内容
    content_html = str(body)
    if len(content_html) > MAX_CONTENT_LEN:
        content_html = content_html[:MAX_CONTENT_LEN]

    content_text = body.get_text(' ', strip=True)
    return {'title': title, 'content_html': content_html, 'content_text': content_text}


def make_desc(html_text, max_len=255):
    """从正文文本提取摘要（前 N 字）"""
    text = re.sub(r'\s+', ' ', html_text or '').strip()
    return text[:max_len]


if __name__ == '__main__':
    # 简单自测
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.cnblogs.com/'
    arts = fetch_article_list(url)
    print(f'列表 {url} 解析到 {len(arts)} 篇：')
    for a in arts[:5]:
        print(' -', a['title'][:40], '|', a['author'], a['pub_time'])
    if arts:
        d = fetch_article_detail(arts[0]['url'])
        print('\n详情页:', d['title'][:40])
        print('正文长度:', len(d['content_html']), '含代码块:', '<pre' in d['content_html'])

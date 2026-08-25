from datetime import date

from django import template
from django.db.models import Count, Q

from app01 import models
from app01.models import Article

register = template.Library()

#自定义inclusion_tag
@register.inclusion_tag('left_menu.html')
def left_menu(username):
    user_obj = models.UserInfo.objects.filter(username=username).first()

    # 获取当前用户所有文章
    blog = user_obj.blog
    # 1.获取当前站点文章用到的所有标签以及标签下文章数
    tag_list = models.Tag.objects.filter(article__blog=blog).annotate(
        count_num=Count('article', filter=Q(article__blog=blog))
    ).values_list('name', 'count_num')
    # 2.获取当前站点文章用到的所有分类以及分类下文章数
    category_list = models.Category.objects.filter(article__blog=blog).annotate(
        count_num=Count('article', filter=Q(article__blog=blog))
    ).values_list('name', 'count_num')
    # 传给前端JS：所有有文章的日期字符串列表 "2026-08-11"
    # 取出原始时间
    time_list = Article.objects.filter(blog=blog).values_list("create_time", flat=True)
    has_date_str = []
    for t in time_list:
        if t:
            has_date_str.append(t.strftime("%Y-%m-%d"))

    # 默认初始展示当前年月
    now = date.today()
    init_year = now.year
    init_month = now.month

    return {
        'username': username,
        'tag_list': tag_list,
        'category_list': category_list,
        'has_date_str': has_date_str,
        'init_year': init_year,
        'init_month': init_month,
    }
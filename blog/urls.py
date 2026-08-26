"""
URL configuration for blog project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, re_path
from django.views.static import serve

from app01 import views
from blog import settings

urlpatterns = [
    path('', lambda req: redirect('/home/')),
    path('admin/', admin.site.urls),
    path('pet/stats/',views.pet_stats),
    path('pet/chat/',views.pet_chat),
    path('pet/balance/',views.pet_balance),
    path('register/',views.register,name='register'),
    path('login/',views.login),
    path('get_code/',views.get_code),
    path('home/',views.home),
    path('logout/',views.logout),
    path('set_password/',views.set_password),
    path('up_or_down/',views.up_or_down),
    path('comment/',views.comment),
    path('backend/',views.backend),
    path('crawl/',views.crawl_page),
    path('crawl/list/',views.crawl_article_list),
    path('crawl/import/',views.crawl_import),
    path('dashboard/',views.dashboard),
    path('add_article/',views.add_article),
    path('add_category/',views.add_category),
    path('add_tag/',views.add_tag),
    path('edit_user/',views.edit_user),
    re_path('media/(?P<path>.*)',serve,{'document_root':settings.MEDIA_ROOT}),
    re_path('edit/article/(?P<article_id>\d+)',views.edit_article),
    re_path('edit/category/(?P<category_id>\d+)',views.edit_category),
    re_path('edit/tag/(?P<tag_id>\d+)',views.edit_tag),
    re_path('delete/article/(?P<article_id>\d+)',views.delete_article),
    re_path('delete/comment/(?P<comment_id>\d+)',views.delete_comment),
    re_path('delete/category/(?P<category_id>\d+)',views.delete_category),
    re_path('delete/tag/(?P<tag_id>\d+)',views.delete_tag),
    re_path('(?P<username>\w+)/(?P<condition>category|tag|archive)/(?P<param>.+)/',views.site),
    #分类过滤：用户名/category/分类id
    #标签过滤：用户名/tag/标签id
    #月份过滤：用户名/archive/年-月
    re_path('(?P<username>\w+)/article/(?P<article_id>\d+)',views.article_detail),
    re_path('(?P<username>\w+)',views.site),

]

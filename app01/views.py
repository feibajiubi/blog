import json
import random
import re
import time

import jieba
import requests
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from blog import settings
from app01 import models
from app01.models import Article
from app01.myform import regform
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
from django.db.models.functions import TruncMonth
from django.db.models import Count, Q
from datetime import date,datetime
from bs4 import BeautifulSoup

def register(request):
    form_obj=regform.RegForm
    if request.method == 'POST':
        back_dict={'code':0,'msg':''}
        form_obj=regform.RegForm(request.POST)
        if form_obj.is_valid():
            #保存数据
            clean_data=form_obj.cleaned_data
            #将confirm_password去除
            clean_data.pop('confirm_password')
            #操作数据库保存数据
            #**clean_data:以关键字参数给函数传参
            models.UserInfo.objects.create_user(**clean_data)
            back_dict['url']='/login/'
            return JsonResponse(back_dict)
        else:
            back_dict['code']=1001
            back_dict['msg']=form_obj.errors
            print(back_dict)
        return JsonResponse(back_dict)
    return render(request,'register.html',locals())

def login(request):
    if request.method == 'POST':
        back_dict={'code':0,'msg':''}
        username=request.POST.get('username')
        password=request.POST.get('password')
        code=request.POST.get('code')
        session_code=request.session.get('code')
        # 验证码校验（session中无验证码时直接提示，避免None.upper()报错）
        if not session_code or session_code.upper()!= (code or '').upper():
            back_dict['code']=1002
            back_dict['msg']='验证码错误或已过期，请刷新后重试'
            return JsonResponse(back_dict)
        #判断用户和密码是否正确
        user_obj=auth.authenticate(request,username=username,password=password)
        if user_obj:#查询成功
            #保存用户状态
            auth.login(request,user_obj)
            target_url=request.GET.get('next')
            if target_url:
                back_dict['url']=target_url
            else:
                back_dict['url']='/home/'
        else:
            back_dict['code']=1001
            back_dict['msg']='用户或密码错误'
        return JsonResponse(back_dict)
    return render(request,'login.html')


def get_random():
    return random.randint(0,255),random.randint(0,255),random.randint(0,255)

def get_code(request):
    #利用pillow模块
    img_obj=Image.new('RGB',(400,35),get_random())#创建空白图片(彩色，宽，高，三原色)
    img_draw=ImageDraw.Draw(img_obj)#产生一支在这张图上作画的笔
    img_font=ImageFont.truetype('static/js/111.ttf.ttf',30)#产生字体样式
    #获取内存管理器对象
    io_obj=BytesIO()
    #生成随机验证码：5个随机的大写字母，或者小写字母或者数字
    code=''
    for i in range(5):
        random_upper = chr(random.randint(65, 90))
        random_lower = chr(random.randint(97, 122))#通过ascii码将数字转换成对应的子母
        random_int = str(random.randint(0, 9))
        #从上面三种情况随机获取一个
        tem=random.choice([random_upper,random_lower,random_int])
        #将字符写到图片上
        img_draw.text((65*(i+1),0),tem,get_random(),img_font)
        code+=tem
        #随机验证码在登录视图使用，所以保存到session中
    request.session['code']=code
    img_obj.save(io_obj,'png')
    #再讲图片读取出来返回给前端页面
    data=io_obj.getvalue()
    return HttpResponse(data)

def home(request):
    # 首页文章：按发布时间倒序（最新在前）
    article_queryset=models.Article.objects.all().order_by('-create_time','-id')

    # 获取所有分类和标签，供首页筛选悬浮框使用
    all_categories=models.Category.objects.all()
    all_tags=models.Tag.objects.all()

    # 当前筛选状态
    current_category=request.GET.get('category','')
    current_tag=request.GET.get('tag','')
    current_liked=request.GET.get('liked','')
    search_q=request.GET.get('q','')

    # 按搜索关键词筛选（匹配文章标题）
    if search_q:
        article_queryset=article_queryset.filter(title__icontains=search_q)

    # 按分类筛选
    if current_category:
        article_queryset=article_queryset.filter(category__name=current_category)

    # 按标签筛选
    if current_tag:
        article_queryset=article_queryset.filter(tags__name=current_tag)

    # 按赞过筛选（当前登录用户点赞过的文章）
    if current_liked=='1' and request.user.is_authenticated:
        liked_ids=models.UpAndDown.objects.filter(
            user=request.user,is_up=True
        ).values_list('article_id',flat=True)
        article_queryset=article_queryset.filter(id__in=liked_ids)

    # 右侧排行数据
    # 阅读排行：按阅读量降序取前10
    read_rank=models.Article.objects.all().order_by('-read_num')[:10]
    # 点赞排行：按点赞数降序取前10
    up_rank=models.Article.objects.all().order_by('-up_num')[:10]
    # 作者推荐：所有博客站点
    blog_list=models.Blog.objects.all()

    # 分页：每页12篇（仿博客园）
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(article_queryset, 12)
    page_num = request.GET.get('page')
    try:
        article_page = paginator.page(page_num)
    except PageNotAnInteger:
        article_page = paginator.page(1)
    except EmptyPage:
        article_page = paginator.page(paginator.num_pages)

    return render(request,'home.html',locals())

@login_required
def logout(request):
    auth.logout(request)
    return redirect('/home/')

@login_required
def set_password(request):
    if request.method=='POST':
        back_dict={'code':0,'msg':''}
        old_password=request.POST.get('old_password')
        new_password=request.POST.get('new_password')
        confirm_password=request.POST.get('confirm_password')
        #校验旧密码是否正确
        is_right=request.user.check_password(old_password)
        if is_right:
            #判断两次密码是否一致
            if new_password==confirm_password:
                #修改密码
                request.user.set_password(new_password)
                request.user.save()
                back_dict['msg']='修改成功'
            else:
                back_dict['code']=1001
                back_dict['msg']='两次密码不一致'
        else:
            back_dict['code'] = 1002
            back_dict['msg'] = '原密码错误'
        return JsonResponse(back_dict)

def site(request,username,**kwargs):
    user_obj=models.UserInfo.objects.filter(username=username).first()
    if not user_obj:
        return render(request,'error.html',locals())
    #获取当前用户所有文章（按发布时间倒序，最新在前）
    blog=user_obj.blog
    article_queryset=models.Article.objects.filter(blog=blog).order_by('-create_time','-id')
    #如果还有多余参数，还需要再次过滤
    if kwargs:
        condition=kwargs.get('condition')
        param=kwargs.get('param')
        if condition=='category':#对分类再次进行过滤
            article_queryset=article_queryset.filter(category__name=param)
        elif condition=='tag':#对标签再次进行过滤
            article_queryset=article_queryset.filter(tags__name=param)
        elif condition=='archive':
            try:
                target_day = datetime.strptime(param, "%Y-%m-%d").date()
                article_queryset = article_queryset.filter(create_time=target_day)
            except ValueError:
                article_queryset = Article.objects.none()
    #1.获取当前站点文章用到的所有标签以及标签下文章数
    tag_list=models.Tag.objects.filter(article__blog=blog).annotate(
        count_num=Count('article', filter=Q(article__blog=blog))
    ).values_list('name','count_num')
    #2.获取当前站点文章用到的所有分类以及分类下文章数
    category_list=models.Category.objects.filter(article__blog=blog).annotate(
        count_num=Count('article', filter=Q(article__blog=blog))
    ).values_list('name','count_num')
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

    # 该站点全部文章的汇总统计（不受当前筛选条件影响）
    from django.db.models import Sum as _Sum
    blog_stats = models.Article.objects.filter(blog=blog).aggregate(
        total=Count('id'),
        read=_Sum('read_num') or 0,
        up=_Sum('up_num') or 0,
        down=_Sum('down_num') or 0,
        comment=_Sum('comment_num') or 0,
    )

    # 分页：每页12篇（仿博客园）
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(article_queryset, 12)
    page_num = request.GET.get('page')
    try:
        article_page = paginator.page(page_num)
    except PageNotAnInteger:
        article_page = paginator.page(1)
    except EmptyPage:
        article_page = paginator.page(paginator.num_pages)

    return render(request,'site.html',locals())

def article_detail(request,username,article_id):
    user_obj=models.UserInfo.objects.filter(username=username).first()
    blog=user_obj.blog
    #同时满足用户名和文章id的数据

    article_obj=models.Article.objects.filter(blog=blog,id=article_id).first()
    comment_list=models.Comment.objects.filter(article=article_obj)

    if not article_obj:
        return render(request,'error.html')
    # 阅读量+1（F表达式原子更新，避免并发竞态）
    models.Article.objects.filter(id=article_obj.id).update(read_num=F('read_num')+1)
    article_obj.read_num += 1
    return render(request,'article_detail.html',locals())

def up_or_down(request):
    if request.method=='POST':
        back_dict={'code':0,'msg':''}
        article_id=request.POST.get('article_id')
        article_obj=models.Article.objects.filter(id=article_id).first()
        is_up=request.POST.get('is_up')#前端数据格式
        is_up=json.loads(is_up)#将json字符串true转换成python布尔值
        #1.判断是否登录
        if request.user.is_authenticated:
            #2.判断当前文章是否是当前用户写的
            if article_obj.blog.userinfo==request.user:
                back_dict['code']=1001
                back_dict['msg']='不能给自己点赞'
            else:
                #3.查询用户是否给这篇文章点过
                is_click=models.UpAndDown.objects.filter(user=request.user,article=article_obj).first()
                if not is_click:#没点过，正常点赞/点踩
                    if is_up:
                        article_obj.up_num+=1
                        back_dict['msg']='点赞成功'
                    else:
                        article_obj.down_num+=1
                        back_dict['msg']='点踩成功'
                    article_obj.save()
                    models.UpAndDown.objects.create(user=request.user,article=article_obj,is_up=is_up)
                else:#已经点过了
                    if is_click.is_up==is_up:
                        #点的和之前一样，取消
                        if is_up:
                            article_obj.up_num-=1
                        else:
                            article_obj.down_num-=1
                        article_obj.save()
                        is_click.delete()
                        #取消不提示，msg留空
                        back_dict['msg']=''
                    else:
                        #点的和之前不一样，切换
                        if is_up:
                            #之前是点踩，现在改成点赞
                            article_obj.down_num-=1
                            article_obj.up_num+=1
                            back_dict['msg']='点赞成功'
                        else:
                            #之前是点赞，现在改成点踩
                            article_obj.up_num-=1
                            article_obj.down_num+=1
                            back_dict['msg']='点踩成功'
                        article_obj.save()
                        is_click.is_up=is_up
                        is_click.save()
                #返回最新的点赞点踩数
                back_dict['up_num']=article_obj.up_num
                back_dict['down_num']=article_obj.down_num
        else:#用户没登录
            back_dict['code']=1003
            back_dict['msg']='请先<a href="/login/">登录</a>'
        return JsonResponse(back_dict)

def comment(request):
    back_dict={'code':0,'msg':''}
    if request.method=='POST':
        article_id=request.POST.get('article_id')
        content=request.POST.get('content')
        parent_id=request.POST.get('parent_id')
        article_obj=models.Article.objects.filter(id=article_id).first()
        if request.user.is_authenticated:
            #直接操作数据库保存数据
            models.Article.objects.filter(pk=article_id).update(comment_num=F('comment_num')+1)
            models.Comment.objects.create(user=request.user,article=article_obj,content=content,parent_id=parent_id)
            back_dict['msg']='评论成功'
        else:
            back_dict['code']=1001
            back_dict['msg']='用户未登录'
        return JsonResponse(back_dict)

@login_required
def backend(request):
    #获取当前用户所有文章
    user_obj=models.UserInfo.objects.filter(username=request.user.username).first()
    blog=user_obj.blog
    article_queryset=models.Article.objects.filter(blog=blog)
    category_queryset=models.Category.objects.all()
    tag_queryset = models.Tag.objects.all()
    comment_queryset=models.Comment.objects.filter(user=user_obj)
    return render(request,'backend/backend.html',locals())

@login_required
def add_article(request):
    #获取所有分类和标签
    user_obj=models.UserInfo.objects.filter(username=request.user.username).first()
    blog=user_obj.blog
    category_queryset=models.Category.objects.all()
    tag_queryset=models.Tag.objects.all()
    if request.method=='POST':
        title=request.POST.get('title')
        content=request.POST.get('content')
        category_id=request.POST.get('category')
        tag_list=request.POST.getlist('tags')
        #利用模块处理简介
        soup=BeautifulSoup(content,'html.parser')
        #找到script标签
        script_tags=soup.find_all('script')
        for i in script_tags:
            i.decompose()#删除找到的script标签
        desc=soup.text[0:255]

        #保存数据
        article_obj=models.Article.objects.create(title=title,content=str(soup),desc=desc,category_id=category_id,blog=blog)
        #添加文章和标签之间的一个关系
        article_obj.tags.add(*tag_list)
        return redirect('/backend/')
    return render(request,'backend/add_article.html',locals())

@login_required
def add_category(request):
    # 获取当前用户所有分类
    user_obj = models.UserInfo.objects.filter(username=request.user.username).first()
    blog = user_obj.blog
    username = request.user.username
    category_queryset = models.Category.objects.filter(blogs=blog).annotate(
        count_num=Count('article', filter=Q(article__blog=blog))
    )
    if request.method == 'POST':
        category_name = request.POST.get('category')
        if category_name:
            category_obj = models.Category.objects.create(name=category_name)
            category_obj.blogs.add(blog)
        return redirect('/add_category/')
    return render(request, 'backend/add_category.html', locals())


@login_required
def add_tag(request):
    # 获取当前用户所有标签
    user_obj = models.UserInfo.objects.filter(username=request.user.username).first()
    blog = user_obj.blog
    username = request.user.username
    tag_queryset = models.Tag.objects.filter(blogs=blog).annotate(
        count_num=Count('article', filter=Q(article__blog=blog))
    )
    if request.method == 'POST':
        tag_name = request.POST.get('tag')
        if tag_name:
            tag_obj = models.Tag.objects.create(name=tag_name)
            tag_obj.blogs.add(blog)
        return redirect('/backend/')
    return render(request, 'backend/add_tag.html', locals())


@login_required
def edit_article(request,article_id):
    #获取所有标签和分类
    user_obj = models.UserInfo.objects.filter(username=request.user.username).first()
    blog = user_obj.blog
    category_queryset = models.Category.objects.all()
    tag_queryset = models.Tag.objects.all()
    article_obj=models.Article.objects.filter(id=article_id,blog=blog).first()
    if request.method=='POST':
        title=request.POST.get('title')
        content=request.POST.get('content')
        category_id=request.POST.get('category')
        tag_list=request.POST.getlist('tags')
        # 利用模块处理简介
        soup = BeautifulSoup(content, 'html.parser')
        # 找到script标签
        script_tags = soup.find_all('script')
        for i in script_tags:
            i.decompose()  # 删除找到的script标签
        desc = soup.text[0:255]
        models.Article.objects.filter(id=article_id,blog=blog).update(title=title,content=str(soup),category_id=category_id)
        article_obj.tags.set(tag_list)
        return redirect('/backend/')
    return render(request,'backend/edit_article.html',locals())

@login_required
def delete_article(request,article_id):
    models.Article.objects.filter(id=article_id).delete()
    return redirect('/backend/#article')

@login_required
def delete_comment(request,comment_id):
    models.Comment.objects.filter(id=comment_id).delete()
    return redirect('/backend/#comment')

@login_required
def delete_category(request,category_id):
    models.Category.objects.filter(id=category_id).delete()
    return redirect('/backend/#category')

@login_required
def edit_category(request,category_id):
    if request.method=='POST':
        new_name=request.POST.get('name')
        if new_name:
            models.Category.objects.filter(pk=category_id).update(name=new_name)
            return JsonResponse({'code':0,'msg':'修改成功'})
    return JsonResponse({'code':1,'msg':'修改失败'})

@login_required
def delete_tag(request,tag_id):
    models.Tag.objects.filter(id=tag_id).delete()
    return redirect('/backend/#tag')

@login_required
def edit_tag(request,tag_id):
    if request.method=='POST':
        new_name=request.POST.get('name')
        if new_name:
            models.Tag.objects.filter(pk=tag_id).update(name=new_name)
            return JsonResponse({'code':0,'msg':'修改成功'})
    return JsonResponse({'code':1,'msg':'修改失败'})

@login_required
def edit_user(request):
    # 直接用request.user，避免重新查询出问题
    user_obj=request.user
    blog=user_obj.blog
    if request.method=='POST':
        # 判断是头像上传还是个人信息修改
        if request.FILES.get('avatar'):
            # 头像上传
            avatar=request.FILES.get('avatar')
            if avatar:
                user_obj.avatar=avatar
                user_obj.save()
            return redirect('/home/')
        else:
            # 个人信息修改（AJAX）
            back_dict={'code':0,'msg':''}
            phone=request.POST.get('phone') or ''
            email=request.POST.get('email') or ''
            site_name=request.POST.get('site_name')
            site_title=request.POST.get('site_title')
            site_theme=request.FILES.get('site_theme')
            #验证手机号是否符合格式（非空才校验）
            if phone:
                ret=re.match('1[3-9]\d{9}',phone)
                if not ret:
                    back_dict['code']=1001
                    back_dict['phone']='请输入正确格式的手机号'
                    return JsonResponse(back_dict)
            #邮箱格式校验（非空才校验）
            if email:
                email_right=re.match('\w+@\w+\.\w+',email)
                if not email_right:
                    back_dict['code']=1002
                    back_dict['email']='请输入正确的邮箱格式'
                    return JsonResponse(back_dict)
            #操作数据库进行保存
            models.UserInfo.objects.filter(pk=user_obj.pk).update(phone=phone,email=email)
            # 处理站点信息
            blog_id = user_obj.blog_id
            if not blog_id:
                # 用户没有站点，自动创建一个并关联
                blog_obj = models.Blog.objects.create(
                    site_name=site_name,
                    site_title=site_title,
                )
                if site_theme:
                    blog_obj.site_theme = site_theme
                    blog_obj.save()
                # 关联到当前用户
                user_obj.blog = blog_obj
                user_obj.save()
            else:
                # 已有站点，更新
                blog_obj = models.Blog.objects.filter(pk=blog_id).first()
                if blog_obj:
                    blog_obj.site_name = site_name
                    blog_obj.site_title = site_title
                    if site_theme:
                        blog_obj.site_theme = site_theme
                    blog_obj.save()
            return JsonResponse(back_dict)
    return render(request,'backend/edit_user.html',locals())


# ==================== 鲸鱼娘宠物助手 ====================

@csrf_exempt
def pet_stats(request):
    """宠物助手统计接口：
    默认返回博客全站数据；带 ?blog=<用户名> 返回该站点汇总；
    带 ?article=<文章id> 返回当前文章数据（优先）
    """
    from django.db.models import Sum
    article_id = request.GET.get('article', '').strip()
    article_stats = None
    if article_id and article_id.isdigit():
        a = models.Article.objects.filter(id=int(article_id)).select_related('blog__userinfo').first()
        if a:
            article_stats = {
                'article_id': a.id,
                'title': a.title,
                'author': a.blog.userinfo.username if a.blog and a.blog.userinfo else '',
                'up': a.up_num,
                'down': a.down_num,
                'read': a.read_num,
                'comment': a.comment_num,
            }
    blog_name = request.GET.get('blog', '').strip()
    blog_stats = None
    if blog_name:
        # 查找该用户名对应的站点
        user_obj = models.UserInfo.objects.filter(username=blog_name).select_related('blog').first()
        if user_obj and user_obj.blog:
            blog = user_obj.blog
            agg = models.Article.objects.filter(blog=blog).aggregate(
                total=Count('id'),
                read=Sum('read_num') or 0,
                up=Sum('up_num') or 0,
                down=Sum('down_num') or 0,
                comment=Sum('comment_num') or 0,
            )
            blog_stats = {
                'blog': blog_name,
                'site_title': blog.site_title,
                'stats': agg,
            }
    # 全站统计
    agg_all = models.Article.objects.aggregate(
        total=Count('id'),
        read=Sum('read_num') or 0,
        up=Sum('up_num') or 0,
        down=Sum('down_num') or 0,
        comment=Sum('comment_num') or 0,
    )
    return JsonResponse({
        'ok': True,
        'logged_in': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else '',
        'blog_count': models.Blog.objects.count(),
        'category_count': models.Category.objects.count(),
        'tag_count': models.Tag.objects.count(),
        'stats': agg_all,
        'blog_stats': blog_stats,       # 命中站点时非空
        'article_stats': article_stats, # 命中文章时非空
    })


# RAG 知识库：分词检索相关文章
_STOP_WORDS = set('的了和是在有这我你他她它们什么怎么为什么吗呢吧啊呀哦嗯啊哈的么一个可以能不能请问告诉').union(
    {'的', '了', '和', '是', '在', '有', '这', '我', '你', '他', '她', '它', '们', '什么', '怎么', '为什么',
     '吗', '呢', '吧', '啊', '呀', '哦', '嗯', '哈', '个', '可以', '能', '不能', '请问', '告诉', '一下', '一些'})


def _rag_search(query, top_n=3):
    """用 jieba 分词 + 关键词匹配检索文章，返回 [{title,url,desc,score}]"""
    words = [w for w in jieba.cut(query) if len(w) > 1 and w not in _STOP_WORDS]
    if not words:
        # 全部是停用词时退化为空检索
        return []
    articles = models.Article.objects.select_related('blog__userinfo').all()
    scored = []
    for a in articles:
        score = 0
        title_hit = [w for w in words if w in a.title]
        content_hit = [w for w in words if w in a.content]
        score += len(title_hit) * 3 + len(content_hit)
        if score > 0:
            scored.append((score, a, title_hit, content_hit))
    scored.sort(key=lambda x: -x[0])
    results = []
    for score, a, th, ch in scored[:top_n]:
        # 生成摘要：优先显示命中词附近的内容
        snippet = a.desc
        if ch:
            idx = a.content.find(ch[0])
            if idx >= 0:
                start = max(0, idx - 40)
                snippet = a.content[start:idx + 60].replace('\n', ' ')
        results.append({
            'title': a.title,
            'url': f'/{a.blog.userinfo.username}/article/{a.id}',
            'desc': a.desc,
            'snippet': snippet,
            'score': score,
        })
    return results


# 规则对话库
_RULE_REPLIES = [
    (['你好', '您好', '嗨', '哈喽', 'hello', 'hi', '在吗', '在么'],
     ['你好呀~ 我是博客里的小鲸鱼娘 🐋', '嗨嗨！找我有事吗？', '在的在的，一直在这里等你呢~']),
    (['你是谁', '你叫什么', '自我介绍', '介绍你'],
     ['我是小鲸鱼娘，这个博客的 AI 宠物助手 🐋 可以陪你聊天、帮你找文章、播报博客数据哦！']),
    (['能做什么', '会什么', '有什么功能', '帮助', 'help', '功能'],
     ['我可以：\n① 陪你聊天，回答关于这个博客的问题\n② 帮你检索站内文章（知识库问答）\n③ 播报博客数据（点我看统计）\n④ 让你摸摸头~']),
    (['谢谢', '感谢', '多谢', 'thx', 'thanks'],
     ['不客气呀~ 能帮到你就好！(๑•̀ㅂ•́)و✧', '嘿嘿，小事一桩！']),
    (['再见', '拜拜', '走了', '886', 'bye'],
     ['拜拜~ 随时回来找我玩哦 🐋', '再见再见，我会想你的~']),
    (['笨蛋', '傻瓜', '菜', '垃圾', '没用'],
     ['呜……不许这么说我！(｡•́︿•̀｡)', '哼！我可聪明了！会检索文章的！']),
    (['可爱', '好看', '漂亮', '萌萌'],
     ['嘿嘿，谢谢夸奖，我可是专门设计的鲸鱼娘呢 (✿◡‿◡)', '嘻嘻，再多夸我几句！']),
    (['文章', '博客', '推荐', '有什么写的', '看了什么'],
     ['我帮你找找站内文章吧~ 可以直接问我具体内容，比如"关于 Django 的文章"']),
]


def _rule_reply(msg):
    """规则对话：命中返回回复文本，否则返回 None。
    知识性提问（是什么/怎么/为什么/解释/介绍/如何 等）不命中规则，
    交给 AI 或 RAG 处理。
    """
    msg_lower = msg.lower()
    # 知识性提问关键词：这些情况跳过规则，走 AI/RAG
    knowledge_hint = ['是什么', '什么是', '有哪些', '怎么做', '如何', '怎么用', '为什么',
                      '解释', '介绍', '讲讲', '说下', '说一下', '区别', '原理', '用法',
                      'how', 'what is', 'why', '介绍下']
    for h in knowledge_hint:
        if h in msg_lower:
            return None
    for keys, replies in _RULE_REPLIES:
        for k in keys:
            if k in msg_lower:
                return random.choice(replies)
    return None


def _deepseek_reply(system_prompt, user_msg, max_tokens=600):
    """调用 DeepSeek API 生成回复；失败返回 None"""
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        return None
    try:
        resp = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_msg},
                ],
                'max_tokens': max_tokens,
                'stream': False,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception:
        return None


# ---------- DeepSeek 余额查询（60 秒缓存，避免频繁请求官方接口） ----------
_balance_cache = {'ts': 0, 'data': None}
_BALANCE_TTL = 60  # 秒

def get_deepseek_balance(force=False):
    """查询 DeepSeek 账户余额。
    返回 dict：{ok, balance, currency, insufficient, msg}
    - ok=True 且 insufficient=False：余额充足
    - ok=True 且 insufficient=True：余额不足（<=0）
    - ok=False：未配置 key / 查询失败
    """
    import time as _time
    now = _time.time()
    if not force and _balance_cache['data'] and (now - _balance_cache['ts']) < _BALANCE_TTL:
        return _balance_cache['data']
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        return {'ok': False, 'msg': '未配置 DEEPSEEK_API_KEY'}
    try:
        resp = requests.get(
            'https://api.deepseek.com/user/balance',
            headers={'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'},
            timeout=15,
        )
        if resp.status_code != 200:
            result = {'ok': False, 'msg': f'余额接口异常({resp.status_code})'}
            _balance_cache.update({'ts': now, 'data': result})
            return result
        data = resp.json()
        balance = 0.0
        currency = 'CNY'
        infos = data.get('balance_infos') or []
        if infos:
            try:
                balance = float(infos[0].get('total_balance') or 0)
            except (TypeError, ValueError):
                balance = 0.0
            currency = infos[0].get('currency') or 'CNY'
        result = {
            'ok': True,
            'balance': round(balance, 2),
            'currency': currency,
            'insufficient': balance <= 0,
        }
        _balance_cache.update({'ts': now, 'data': result})
        return result
    except Exception as e:
        return {'ok': False, 'msg': f'余额查询失败: {e}'}


@csrf_exempt
def pet_balance(request):
    """宠物助手余额接口：GET 返回 DeepSeek 账户余额"""
    return JsonResponse(get_deepseek_balance())


@csrf_exempt
def pet_chat(request):
    """宠物助手对话接口：
    1) 规则对话优先；2) RAG 检索站内文章；
    3) 配置了 DEEPSEEK_API_KEY 时，用检索到的文章作为知识库让 AI 生成回答；
       未配置时返回规则回复 + 相关文章链接。
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'msg': '仅支持 POST'})
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST
    msg = (data.get('msg') or '').strip()
    if not msg:
        return JsonResponse({'ok': False, 'msg': '消息不能为空'})
    if len(msg) > 500:
        msg = msg[:500]

    # 1. 规则对话（无论是否配置 API key 都优先）
    rule_text = _rule_reply(msg)
    if rule_text:
        return JsonResponse({'ok': True, 'reply': rule_text, 'mode': 'rule'})

    # 2. RAG 检索站内文章
    hits = _rag_search(msg)
    has_key = bool(settings.DEEPSEEK_API_KEY)

    # 3a. 有 API key：用知识库让 AI 生成回答（先检查余额）
    if has_key:
        bal = get_deepseek_balance()
        if bal.get('ok') and bal.get('insufficient'):
            return JsonResponse({
                'ok': True,
                'reply': '呜……我的余额不足了 (｡•́︿•̀｡) 请先去 DeepSeek 平台充值，我才能继续回答问题哦~',
                'mode': 'no_balance',
                'balance': bal,
            })
        if hits:
            knowledge = '\n\n'.join(
                f'【文章{idx + 1}】标题：{h["title"]}\n摘要：{h["snippet"]}\n链接：/{{博客}}/article/…'
                for idx, h in enumerate(hits)
            )
            system_prompt = (
                '你是这个博客站点里的 AI 宠物助手"小鲸鱼娘"，说话风格可爱活泼、带少量颜文字。'
                '下面是从该博客站内检索到的相关知识，请基于这些内容回答用户的问题；'
                '如果知识不足以回答，就如实说明，并推荐用户点开相关文章看看。\n\n'
                f'站内相关知识：\n{knowledge}'
            )
        else:
            system_prompt = (
                '你是这个博客站点里的 AI 宠物助手"小鲸鱼娘"，说话风格可爱活泼、带少量颜文字。'
                '用户问的内容在博客里没有检索到相关文章，请如实告诉用户没找到相关文章，'
                '并简单给一些建议（比如换个关键词，或去首页逛逛）。'
            )
        ai_reply = _deepseek_reply(system_prompt, msg)
        if ai_reply:
            return JsonResponse({
                'ok': True,
                'reply': ai_reply,
                'mode': 'ai',
                'hits': hits,
            })

    # 3b. 无 API key（或 AI 调用失败）：规则兜底 + 返回相关文章
    if hits:
        lines = ['我在知识库里找到这些相关文章，点进去看看吧~']
        for idx, h in enumerate(hits):
            lines.append(f'{idx + 1}. 《{h["title"]}》 {h["url"]}')
        lines.append('（配置 DeepSeek API Key 后，我可以直接总结文章内容回答你哦）')
        return JsonResponse({'ok': True, 'reply': '\n'.join(lines), 'mode': 'rag', 'hits': hits})

    fallback = random.choice([
        '这个话题我还没学到呢……不过你可以去首页看看有没有相关文章！',
        '唔……我翻了翻知识库没找到相关的。换个问法试试？比如直接问"XX 是什么"',
        '这个问题难倒我啦 (￣▽￣*) 去首页搜搜看关键词吧~',
    ])
    return JsonResponse({'ok': True, 'reply': fallback, 'mode': 'fallback', 'hits': []})


# ==================== 文章导入爬虫 ====================

@login_required
def crawl_page(request):
    """文章导入页面"""
    # 爬取历史记录
    crawl_records = models.CrawlRecord.objects.all().order_by('-create_time')[:20]
    return render(request, 'backend/crawl.html', locals())


@login_required
def crawl_article_list(request):
    """AJAX：爬取指定 URL 的列表页，返回候选文章"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'msg': '仅支持 POST'})
    url = request.POST.get('url', '').strip()
    if not url:
        return JsonResponse({'ok': False, 'msg': '请输入博客园列表页地址'})
    if not url.startswith('http'):
        url = 'https://' + url
    # 记录爬取历史
    record = models.CrawlRecord.objects.create(url=url, status='running')
    try:
        from app01 import crawler
        articles = crawler.fetch_article_list(url)
        if not articles:
            record.status = 'empty'
            record.error_msg = '未解析到任何文章，请确认是博客园列表页'
            record.save()
            return JsonResponse({'ok': False, 'msg': '未解析到文章，请确认是博客园列表页地址'})
        record.status = 'success'
        record.article_count = len(articles)
        record.save()
        return JsonResponse({'ok': True, 'articles': articles, 'count': len(articles)})
    except Exception as e:
        record.status = 'error'
        record.error_msg = str(e)[:500]
        record.save()
        return JsonResponse({'ok': False, 'msg': f'爬取失败：{e}'})


@login_required
def crawl_import(request):
    """AJAX：导入选中的文章（按 title+source_url 去重）"""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'msg': '仅支持 POST'})
    urls = request.POST.getlist('urls[]')
    if not urls:
        return JsonResponse({'ok': False, 'msg': '请先勾选要导入的文章'})
    user_obj = models.UserInfo.objects.filter(username=request.user.username).select_related('blog').first()
    blog = user_obj.blog if user_obj else None
    if not blog:
        return JsonResponse({'ok': False, 'msg': '你还没有个人站点，请先在个人信息中创建'})
    # 默认分类：复用"转载"分类，不存在则创建一个
    category = models.Category.objects.filter(name='转载').first()
    if not category:
        category = models.Category.objects.create(name='转载')
        category.blogs.add(blog)

    from app01 import crawler
    imported, skipped, failed = 0, 0, 0
    errors = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            # 去重：source_url 相同，或标题相同
            detail = crawler.fetch_article_detail(url)
            title = detail['title'].strip()
            if not title or not detail['content_html']:
                failed += 1
                errors.append(f'{url}: 正文为空')
                continue
            exists = models.Article.objects.filter(
                Q(source_url=url) | Q(title=title)
            ).exists()
            if exists:
                skipped += 1
                continue
            desc = crawler.make_desc(detail['content_text'])
            article = models.Article.objects.create(
                title=title,
                desc=desc,
                content=detail['content_html'],
                blog=blog,
                category=category,
                source='转载',
                source_url=url,
            )
            imported += 1
        except Exception as e:
            failed += 1
            errors.append(f'{url}: {e}')
    return JsonResponse({
        'ok': True,
        'imported': imported,
        'skipped': skipped,
        'failed': failed,
        'errors': errors[:10],
    })


# ==================== 数据看板 ====================

@login_required
def dashboard(request):
    """数据看板：文章/阅读/点赞/评论/用户/分类/标签统计 + 词云"""
    from django.db.models.functions import TruncMonth

    # ---- 概览 ----
    overview = {
        'articles': models.Article.objects.count(),
        'reads': models.Article.objects.aggregate(total=Sum('read_num'))['total'] or 0,
        'ups': models.Article.objects.aggregate(total=Sum('up_num'))['total'] or 0,
        'comments': models.Article.objects.aggregate(total=Sum('comment_num'))['total'] or 0,
        'users': models.UserInfo.objects.count(),
        'categories': models.Category.objects.count(),
        'tags': models.Tag.objects.count(),
    }

    # ---- 近12个月发文趋势 ----
    import datetime
    today = date.today()
    # 起始日期 = 12 个月前（含当月共 12 个月）的月初
    start = today.replace(day=1)
    for _ in range(11):
        m = start.month - 1
        y = start.year
        if m == 0:
            m = 12
            y -= 1
        start = datetime.date(y, m, 1)
    month_qs = (models.Article.objects
                .filter(create_time__gte=start)
                .annotate(month=TruncMonth('create_time'))
                .values('month')
                .annotate(cnt=Count('id'))
                .order_by('month'))
    month_map = {m['month'].strftime('%Y-%m'): m['cnt'] for m in month_qs if m['month']}
    trend_months, trend_counts = [], []

    def _add_months(d, months):
        """从 date 对象推进 N 个月，返回当月 1 日"""
        m = d.month - 1 + months
        y = d.year + m // 12
        m = m % 12 + 1
        return datetime.date(y, m, 1)

    cur = _add_months(start, 0).replace(day=1)
    for _ in range(12):
        ym = cur.strftime('%Y-%m')
        trend_months.append(ym)
        trend_counts.append(month_map.get(ym, 0))
        cur = _add_months(cur, 1)

    # ---- 分类分布 ----
    cat_qs = (models.Category.objects
              .annotate(cnt=Count('article'))
              .order_by('-cnt'))
    category_names = [c.name for c in cat_qs]
    category_counts = [c.cnt for c in cat_qs]

    # ---- 标签 Top10 ----
    tag_qs = (models.Tag.objects
              .annotate(cnt=Count('article'))
              .order_by('-cnt')[:10])
    tag_names = [t.name for t in tag_qs]
    tag_counts = [t.cnt for t in tag_qs]

    # ---- 排行 Top10（转成 [[标题, 数值]] 结构，供 JS 直接使用）----
    def top_by(field):
        return [[t, n] for t, n in
                models.Article.objects.order_by('-' + field)[:10].values_list('title', field)]

    read_top = top_by('read_num')
    up_top = top_by('up_num')
    comment_top = top_by('comment_num')

    # ---- 用户活跃 Top10（发文最多） ----
    user_qs = (models.UserInfo.objects
               .annotate(cnt=Count('blog__article'))
               .order_by('-cnt')[:10])
    user_names = [u.username for u in user_qs]
    user_counts = [u.cnt for u in user_qs]

    # ---- 词云（jieba 分词 + wordcloud，输出 PNG）----
    wordcloud_url = None
    try:
        all_text = ''
        for title, content in models.Article.objects.values_list('title', 'content')[:200]:
            # 提取纯文本并分词
            plain = re.sub(r'<[^>]+>', ' ', content or '')
            plain = re.sub(r'[\s\u3000]+', ' ', plain)
            all_text += (title or '') + ' ' + plain + ' '
        if len(all_text) > 50:
            import jieba
            from wordcloud import WordCloud
            from PIL import Image
            # 分词 + 过滤单字
            segs = [w for w in jieba.cut(all_text) if len(w.strip()) > 1]
            freq_text = ' '.join(segs)
            font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑
            wc = WordCloud(
                font_path=font_path,
                width=900, height=500,
                background_color='white',
                max_words=100,
                collocations=False,
            ).generate(freq_text)
            # 输出到 media
            import os
            media_dir = os.path.join(settings.MEDIA_ROOT, 'analysis')
            os.makedirs(media_dir, exist_ok=True)
            wc_path = os.path.join(media_dir, 'wordcloud.png')
            wc.to_file(wc_path)
            wordcloud_url = '/media/analysis/wordcloud.png'
    except Exception:
        wordcloud_url = None

    return render(request, 'backend/dashboard.html', locals())

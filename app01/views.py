import json
import random
import re

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

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
            file_obj=request.FILES.get('avatar')
            if file_obj:
                clean_data['avatar']:file_obj
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
    article_queryset=models.Article.objects.all().order_by('-up_num')

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
    #获取当前用户所有文章
    blog=user_obj.blog
    article_queryset=models.Article.objects.filter(blog=blog)
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

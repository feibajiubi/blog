from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class UserInfo(AbstractUser):
    phone=models.BigIntegerField(verbose_name='手机号',null=True,blank=True)
    avatar=models.FileField(upload_to='avatar/',default='avatar/default.png',verbose_name='用户头像')
    create_time=models.DateField(auto_now_add=True)
    blog=models.OneToOneField('Blog',on_delete=models.CASCADE,null=True)

    def __str__(self):
        return self.username

#个人站点表
class Blog(models.Model):
    site_title=models.CharField(max_length=32,verbose_name='站点标题')
    site_name=models.CharField(max_length=32,verbose_name='站点名字')
    #存放css文件/js文件
    site_theme=models.FileField(upload_to='site_theme/',null=True)

    def __str__(self):
        return self.site_name

#文章表
class Article(models.Model):
    title=models.CharField(max_length=255,verbose_name='文章标题')
    desc=models.CharField(max_length=255,verbose_name='文章简介')
    content=models.TextField(verbose_name='文章内容')
    create_time=models.DateField(auto_now_add=True)
    up_num=models.IntegerField(verbose_name='点赞数',default=0)
    down_num = models.IntegerField(verbose_name='点踩数', default=0)
    comment_num=models.IntegerField(verbose_name='评论数',default=0)
    read_num = models.IntegerField(verbose_name='浏览数', default=0)
    blog=models.ForeignKey('Blog',on_delete=models.CASCADE,null=True)
    category=models.ForeignKey('Category',on_delete=models.CASCADE)
    tags=models.ManyToManyField('Tag')

    def __str__(self):
        return self.title

#分类表
class Category(models.Model):
    name=models.CharField(max_length=32,verbose_name='文章分类名')
    blogs = models.ManyToManyField('Blog', blank=True, verbose_name='所属站点')

    def __str__(self):
        return self.name

#标签表
class Tag(models.Model):
    name=models.CharField(max_length=32,verbose_name='文章标签名')
    blogs = models.ManyToManyField('Blog', blank=True, verbose_name='所属站点')

    def __str__(self):
        return self.name

#点赞点踩表
class UpAndDown(models.Model):
    user=models.ForeignKey('UserInfo',on_delete=models.CASCADE,verbose_name='用户')
    article=models.ForeignKey('Article',on_delete=models.CASCADE,verbose_name='文章')
    is_up=models.BooleanField(verbose_name='点赞或点踩')

    def __str__(self):
        return f"{self.user.username}-{self.article.title}"

#评论表
class Comment(models.Model):
    user = models.ForeignKey('UserInfo', on_delete=models.CASCADE, verbose_name='用户')
    article= models.ForeignKey(to='Article',
                               verbose_name='文章',
                               on_delete=models.CASCADE,null=True)
    content=models.CharField(max_length=255,verbose_name='评论内容')
    create_time=models.DateTimeField(auto_now_add=True)
    parent=models.ForeignKey('self',on_delete=models.CASCADE,verbose_name='父评论',null=True,blank=True)

    def __str__(self):
        return self.content[:15]
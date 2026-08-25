from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from app01 import models

# Register your models here.
admin.site.register(models.Article)
admin.site.register(models.Blog)
admin.site.register(models.Comment)
admin.site.register(models.Category)
admin.site.register(models.Tag)
# 使用UserAdmin注册，确保密码在admin中修改时会被正确哈希
admin.site.register(models.UserInfo, UserAdmin)
admin.site.register(models.UpAndDown)
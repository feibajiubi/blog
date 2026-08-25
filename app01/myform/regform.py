from django import forms
from app01 import models
from django.core.validators import RegexValidator

class RegForm(forms.Form):
    username = forms.CharField(max_length=8,min_length=3,label='用户名',
                             error_messages={
                                 'min_length':'用户名至少为3位',
                                 'max_length':'用户名最大为8位',
                                 'required':'用户名不能为空'
                             },
                             widget=forms.TextInput(attrs={'class':'form-control'})
                             )
    password = forms.CharField(max_length=16, min_length=6, label='密码',
                               error_messages={
                                   'min_length': '密码至少为6位',
                                   'max_length': '密码最大为16位',
                                   'required': '密码不能为空'
                               },
                               widget=forms.PasswordInput(attrs={'class': 'form-control'})
                               )
    confirm_password = forms.CharField(max_length=16, min_length=6, label='确认密码',
                               error_messages={
                                   'min_length': '确认密码至少为6位',
                                   'max_length': '确认密码最大为16位',
                                   'required': '确认密码不能为空'
                               },
                               widget=forms.PasswordInput(attrs={'class': 'form-control'})
                               )
    email = forms.EmailField(label='邮箱',error_messages={
        'invalid':'邮箱格式不正确',
        'required':'邮箱不能为空'
    },widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(label='手机号',
                            validators=[RegexValidator('\d+','请输入数字'),
                                            RegexValidator('1[3-9]\d{9}','请输入正确格式的手机号')
                                        ],
                            widget=forms.TextInput(attrs={'class':'form-control'})
                             )
    #局部钩子：用户名是否存在
    def clean_username(self):
        username = self.cleaned_data.get('username')
        is_exists=models.UserInfo.objects.filter(username=username).exists()
        if is_exists:
            self.add_error('username','用户名已存在')
        return username

    #全局钩子：检验两次密码是否一致
    def clean(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password != confirm_password:
            self.add_error('confirm_password', '两次密码不一致')
        return self.cleaned_data

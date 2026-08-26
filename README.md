# 🐋 博客园风格 Django 博客

一个功能完整的博客系统，基于 **Django 4.2 + MySQL + Bootstrap 3**，集成了 **爬虫导入、数据看板、AI 宠物助手** 三大亮点模块，既是个人博客，也是展示爬虫/数据处理/AI 能力的完整作品。

## ✨ 功能亮点

### 📝 博客核心
- 用户注册 / 登录（Pillow 图形验证码）/ 修改密码 / 个人信息与站点设置
- 文章发布（富文本）、分类、标签、归档日历、评论（楼中楼）、点赞/点踩
- 首页：搜索（标题+正文）、分类/标签/赞过筛选、阅读/点赞排行、作者推荐
- 文章按时间倒序 + 每页 12 篇分页（仿博客园）
- 文章详情：统计条、上一篇/下一篇导航

### 🕷️ 文章导入爬虫（博客园）
- 输入博客园列表页 / 用户主页 / 单篇文章链接即可爬取
- 兼容新版/旧版/自定义主题多种页面布局，支持 `#pN` hash 分页
- 导入时 XSS 白名单清洗（保留代码块/图片，剔除脚本/事件属性），按标题+链接去重
- 来源标记「转载」并保留原文链接，爬取历史留痕

### 📊 数据看板（公开可访问）
- 概览卡片：文章 / 阅读 / 点赞 / 评论 / 用户 / 分类标签
- 近 12 个月发文趋势（ECharts 折线图）、分类饼图、标签/用户柱状图
- 阅读 / 点赞 / 评论 Top10 排行
- 全站词云（jieba 分词 + WordCloud，带缓存）

### 🤖 AI 宠物助手（鲸鱼娘）
- 全站悬浮的鲸鱼娘立绘（透明 PNG），可拖拽、左右吸附镜像翻转、点击 Q 弹
- 悬浮显示当前页面信息（文章/站点/全站三级自适应统计）
- 气泡对话：规则对话 → RAG 站内知识检索 → DeepSeek AI 回答（自动降级）
- 余额检测：余额不足时提示充值；输入时气泡不消失、长文本不自动关闭

### 📡 其他
- RSS 订阅（`/rss/`）
- 敏感配置全部走 `.env`（API Key / SECRET_KEY / 数据库密码）

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Django 4.2, Python 3.8 |
| 数据库 | MySQL 8 (utf8mb4) |
| 前端 | Bootstrap 3.4, jQuery 3.7, ECharts 5 |
| 爬虫 | requests + BeautifulSoup4 + lxml |
| 数据分析 | pandas, jieba, wordcloud, matplotlib |
| AI | DeepSeek API（可选） |

## 🚀 快速开始

```bash
# 1. 克隆并安装依赖
git clone <你的仓库地址>
cd blog
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
#   编辑 .env：填入 DJANGO_SECRET_KEY、DB_PASSWORD、DEEPSEEK_API_KEY（可选）

# 3. 初始化数据库
python manage.py migrate

# 4. 启动
python manage.py runserver
```

访问 http://127.0.0.1:8000/ 即可。

## ⚙️ 部署

1. 服务器上 `cp .env.example .env` 并填入真实值
2. 生产环境设置（`.env`）：
   ```
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=你的域名
   ```
3. 收集静态文件：`python manage.py collectstatic`
4. 用 Gunicorn + Nginx 部署（详见 `docs/DEPLOY.md`）

## 📂 项目结构

```
blog/
├── app01/
│   ├── models.py        # 数据模型（用户/文章/分类/标签/评论/爬取记录）
│   ├── views.py         # 全部视图（博客/爬虫/看板/AI宠物）
│   ├── crawler.py       # 博客园爬虫模块（含 XSS 白名单清洗）
│   ├── myform/          # 注册表单
│   └── templatetags/    # 自定义模板标签
├── blog/                # Django 项目配置
├── static/              # 静态资源（含 pet/ 鲸鱼娘挂件）
├── templates/           # 页面模板（backend/ 后台页面）
└── media/               # 用户上传 + 词云输出（不入库 git）
```

## 🔒 安全说明

- 文章内容渲染前经白名单清洗（防 XSS）
- 所有敏感配置在 `.env`，已被 `.gitignore` 排除
- 爬虫导入内容同样经过安全过滤

## 📄 许可证

MIT

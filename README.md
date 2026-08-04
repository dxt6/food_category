# 食品类别分类系统（基于机器学习的食品智能分类实训平台）

本系统依据《河南经贸现场工程师指标参数》"标的5 人工智能场景应用实训案例包"第一项
**"基于机器学习的食品类别分类系统"** 开发建设，是一套轻量化 B/S 架构的 AI 实训演示平台。

## 功能概览
- **前端演示界面**：账号登录、文本采集上传、一键 AI 推理（三级类目 + 路径 + 置信度）、基础数据展示。
- **PC 管理后台**：品类管理（分页）、样本管理（分页）、模型管理（SVM/随机森林切换与重训）、记录查询（分页 + 导出 CSV）、权限管理、操作日志。
- **机器学习管线**：TF-IDF 字符级 n-gram + SVM / 随机森林，支持训练、保存、预测与准确率评测。

## 技术栈
Django 5 · scikit-learn · Bootstrap 5 · Bootstrap Icons · SQLite（可切换 MySQL）· 原生 JavaScript

前端基于 Django 模板渲染，并做了轻量化设计系统（卡片化布局、顶栏导航、列表分页、基于 Django messages 框架的操作反馈），不引入 React/Vue 等前端构建链。

## 环境要求
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（推荐，用于创建虚拟环境与安装依赖）

## 快速开始
```bash
# 1. 用 uv 创建虚拟环境并安装依赖
uv venv .venv
uv pip install -r requirements.txt

# 2. 初始化数据库与内置数据集（首次运行）
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py load_data

# 3. 启动开发服务器
.venv/Scripts/python manage.py runserver 0.0.0.0:8000
# 若 8000 端口被占用，可改用其他端口，例如：
# .venv/Scripts/python manage.py runserver 0.0.0.0:8001
```
浏览器访问 http://127.0.0.1:8000/ （若改用 8001 则访问对应端口），账号：
- 学生：student / student123
- 管理员：admin / admin123

> 详细部署步骤见 [部署实训手册.md](部署实训手册.md)，实训安排见 [实训任务书.md](实训任务书.md)。

## 运行测试
项目包含 Django 单元测试（覆盖推理、模型、视图等）：
```bash
.venv/Scripts/python manage.py test classifier
```

## 目录结构
```
食品类别分类系统/
├── classifier/              # Django 应用
│   ├── templates/           # 前端模板（base/login/demo_home/各后台页）
│   ├── static/              # 前端静态资源（app.css / app.js）
│   ├── ml/                  # 机器学习模块与数据集、模型文件
│   ├── migrations/          # 数据库迁移
│   ├── views.py / models.py / urls.py
│   └── tests.py             # 单元测试
├── foodclassify/            # Django 项目配置（settings / urls / wsgi）
├── manage.py
├── requirements.txt
├── 项目规范文档(SPEC).md     # 前端实施规范
├── 部署实训手册.md
├── 实训任务书.md
├── 模型评测报告.md
└── README.md
```

## 数据集与评测
- 三级食品分类数据集（`classifier/ml/dataset.json`）：8 一级 / 31 二级 / 51 三级 / 1419 标注样本。
- 模型评测见 [模型评测报告.md](模型评测报告.md)。

## 交付物对照（招标参数 标的5-1）
| 完成物 | 对应文件 |
| --- | --- |
| 实训任务书 | 实训任务书.md |
| 简易食品分类数据集 | classifier/ml/dataset.json |
| 全套开源源码 | 本工程 |
| 基础模型评测数据 | 模型评测报告.md + classifier/ml/models/*.meta.json |
| 傻瓜式部署实训手册 | 部署实训手册.md |

# 食品类别分类系统（基于机器学习的食品智能分类实训平台）

本系统依据《河南经贸现场工程师指标参数》"标的5 人工智能场景应用实训案例包"第一项
**"基于机器学习的食品类别分类系统"** 开发建设，是一套轻量化 B/S 架构的 AI 实训演示平台。

## 功能概览
- **前端演示界面**：账号登录、文本采集上传、一键 AI 推理（三级类目 + 路径 + 置信度）、基础数据展示。
- **PC 管理后台**：品类管理、样本管理、模型管理（SVM/随机森林切换与重训）、记录查询导出、权限管理、操作日志。
- **机器学习管线**：TF-IDF 字符级 n-gram + SVM / 随机森林，支持训练、保存、预测与准确率评测。

## 技术栈
Django 5 · scikit-learn · Bootstrap 5 · SQLite（可切换 MySQL）

## 快速开始
```
pip install -r requirements.txt
python manage.py migrate
python manage.py load_data
python manage.py runserver 0.0.0.0:8000
```
浏览器访问 http://127.0.0.1:8000/ ，账号：student/student123（学生）、admin/admin123（管理员）。
详细步骤见 [部署实训手册.md](部署实训手册.md)，实训安排见 [实训任务书.md](实训任务书.md)。

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

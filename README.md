# 食品智能分类与包装缺陷检测实训平台

本平台依据《河南经贸现场工程师指标参数》"标的5 人工智能场景应用实训案例包"开发，包含两项可独立演示的 AI 实训功能：

- **标的5-1 基于机器学习的食品类别分类系统**：文本输入 → 三级类目智能分类（B/S 演示 + PC 管理后台）。
- **标的5-4 食品包装缺陷检测**：图片上传 → YOLOv8 缺陷定位与识别。

两者共用同一套 Django 工程与登录体系，是一套轻量化、易上手的实训演示平台。

## 功能概览

### 文本分类（标的5-1）
- **前端演示界面**：账号登录、文本采集上传、一键 AI 推理（三级类目 + 路径 + 置信度）、基础数据展示（类目占比可视化）。
- **PC 管理后台**：品类管理、样本管理、模型管理（SVM / 随机森林切换与重训）、记录查询与 CSV 导出、权限管理、操作日志。
- **机器学习管线**：TF-IDF 字符级 n-gram + SVM / 随机森林，支持训练、保存、预测与准确率评测。

### 包装缺陷检测（标的5-4）
- **图片识别演示**：上传食品包装图片（或调用摄像头拍照）→ YOLOv8n 模型定位缺陷 → 返回标注图 + 检测明细（类别 + 置信度）+ 检测记录。
- **视觉训练工作台**：审计原始数据、固定训练/验证划分、标签重映射、弱标注说明。
- **管理后台**：视觉模型状态查看、训练、设为默认；检测记录查询与导出。

## 技术栈
Django 5 · scikit-learn · Ultralytics YOLOv8 · PyTorch · Bootstrap 5 · Bootstrap Icons · SQLite（可切换 MySQL）· 原生 JavaScript

> 说明：视觉模块依赖 `torch` / `ultralytics`，安装体积较大（约数百 MB），首次 `uv pip install` 需要一定时间。

## 环境要求
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（推荐，用于创建虚拟环境与安装依赖）

## 快速开始（克隆即可运行）

```powershell
# 1. 克隆仓库
git clone https://github.com/dxt6/food_category.git
cd food_category

# 2. 用 uv 创建虚拟环境并安装依赖
C:\Users\你的用户名\.local\bin\uv.exe venv .venv
C:\Users\你的用户名\.local\bin\uv.exe pip install --python .venv\Scripts\python.exe --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 3. 初始化数据库与内置文本分类数据集
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py load_data

# 4. 启动开发服务器
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
# 若 8000 端口被占用，可改用其他端口，例如 8001：
# .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8001
```

浏览器访问 http://127.0.0.1:8000/ （若改用 8001 则访问对应端口），账号：
- 学生：student / student123
- 管理员：admin / admin123

> **开箱即用**：视觉检测所需的 YOLOv8n 权重文件 `classifier/vision/models/food_package_yolov8n.pt` 已随仓库提供，克隆后**无需训练即可直接在 `/vision/` 页面上传图片做缺陷检测**。

## 使用说明

### 文本分类
1. 登录后进入首页，在文本框输入食品名称 / 描述（如"原味薯片，马铃薯制作的膨化休闲食品"）。
2. 点击「一键 AI 推理」，返回三级类目、类目路径与置信度；下方展示 Top-3 候选。
3. 管理员可在「PC 管理后台」管理品类 / 样本、重训模型、查询与导出推理记录。

### 包装缺陷检测
1. 登录后访问 `/vision/`（或后台「视觉检测」入口），上传一张食品包装图片。
2. 系统调用 YOLOv8n 模型推理，返回带检测框的标注图与缺陷明细（类别 + 置信度）。
3. 检测记录可在「视觉检测记录」中查询、导出。

## 视觉模型训练（可选）

仓库已包含训练好的权重，通常无需重训。如需基于自有数据重训：

```powershell
# 准备 YOLO 数据集（固定训练/验证划分）
.venv\Scripts\python.exe manage.py prepare_vision_dataset

# 训练（默认 YOLOv8n，训练后自动安装最佳权重）
.venv\Scripts\python.exe manage.py train_vision --epochs 30 --device auto
```

> 原始数据中的正常包装作为空标签负样本；已有局部框从原类别编号 `1–4` 重映射为训练类别 `0–3`；缺少局部框的缺陷图使用整图弱标注。页面会明确提示弱监督定位边界。
> 训练原始数据默认读取 `C:\Users\dongxiaotong\Desktop\教学资源开发\食品包装检测_数据集补充\images`（请按实际路径调整或放置自有数据）。

## 数据集与评测
- 三级食品分类数据集（`classifier/ml/dataset.json`）：8 一级 / 31 二级 / 51 三级 / 1419 标注样本。
- 文本分类模型评测见 [模型评测报告.md](模型评测报告.md)。
- 视觉模块实施边界与 AI agent 开发契约见 [食品包装缺陷检测功能规范(SPEC).md](食品包装缺陷检测功能规范(SPEC).md)；文本前端规范见 [项目规范文档(SPEC).md](项目规范文档(SPEC).md)。

## 仓库内容说明（哪些入库 / 哪些不入库）
| 内容 | 是否入库 | 说明 |
| --- | --- | --- |
| 全部源码、模板、静态资源 | ✅ | classifier/、foodclassify/、manage.py 等 |
| 文本分类模型权重 `*.joblib` | ✅ | classifier/ml/models/ |
| **视觉检测权重 `food_package_yolov8n.pt`** | ✅ | **已入库，clone 即跑，无需训练** |
| 数据库 `db.sqlite3` | ❌ | 运行时生成，含本地数据 |
| 上传图片 `media/` | ❌ | 运行时检测图，不入库 |
| 训练产物 `classifier/vision/prepared_dataset/`、`runs/` | ❌ | 训练中间产物；重训时由命令生成 |

## 运行测试
```powershell
.venv\Scripts\python.exe manage.py test classifier
```

## 目录结构
```
food_category/
├── classifier/
│   ├── templates/classifier/   # 前端模板（base/login/demo_home/各后台页/vision_*）
│   ├── static/                  # 前端静态资源（app.css / app.js）
│   ├── ml/                      # 文本分类：数据集、模型（joblib）、训练/预测代码
│   ├── vision/                  # 视觉模块：YOLOv8 数据集/训练/推理管线
│   │   ├── models/              # 已训练权重 food_package_yolov8n.pt（入库）
│   │   ├── prepared_dataset/    # 训练数据集（不入库，prepare_vision_dataset 生成）
│   │   └── runs/                # 训练过程输出（不入库）
│   ├── migrations/              # 数据库迁移（含 0002 视觉检测记录表）
│   ├── management/commands/     # prepare_vision_dataset / train_vision 命令
│   ├── views.py / models.py / urls.py / tests.py
├── foodclassify/                # Django 项目配置（settings / urls / wsgi）
├── media/                       # 运行时上传/标注图（不入库）
├── manage.py
├── requirements.txt
├── 部署实训手册.md / 实训任务书.md / 模型评测报告.md
├── 项目规范文档(SPEC).md / 食品包装缺陷检测功能规范(SPEC).md
└── README.md
```

## 交付物对照（招标参数 标的5）
| 完成物 | 对应文件 |
| --- | --- |
| 实训任务书 | 实训任务书.md |
| 简易食品分类数据集 | classifier/ml/dataset.json |
| 全套开源源码 | 本工程 |
| 基础模型评测数据 | 模型评测报告.md + classifier/ml/models/*.meta.json |
| 傻瓜式部署实训手册 | 部署实训手册.md |
| 视觉检测模型权重 | classifier/vision/models/food_package_yolov8n.pt |
| 视觉检测功能规范 | 食品包装缺陷检测功能规范(SPEC).md |

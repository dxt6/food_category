# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse

from .models import (
    FoodCategory, FoodSample, PredictionRecord, UserProfile,
    SiteConfig, OperationLog,
)
from .ml import classifier as ml


# ---------------- 工具 ----------------
def get_role(user):
    if not user or not user.is_authenticated:
        return None
    p = getattr(user, "profile", None)
    return p.role if p else None


def admin_required(view):
    @login_required
    def wrapper(request, *args, **kwargs):
        if get_role(request.user) != "admin":
            return redirect("demo_home")
        return view(request, *args, **kwargs)
    return wrapper


def get_default_model():
    cfg, _ = SiteConfig.objects.get_or_create(key="default_model", defaults={"value": "svm"})
    return cfg.value


def log_op(request, action, detail=""):
    OperationLog.objects.create(user=request.user, action=action, detail=detail)


def paginated_context(request, queryset, per_page):
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return {"page_obj": page_obj, "querystring": query_params.urlencode()}


# ---------------- 演示端 ----------------
def login_view(request):
    error = ""
    username = request.POST.get("username", "").strip()
    if request.method == "POST":
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("admin_dashboard" if get_role(user) == "admin" else "demo_home")
        error = "用户名或密码错误"
    return render(request, "classifier/login.html", {"error": error, "username": username})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def demo_home(request):
    result = None
    if request.method == "POST":
        text = request.POST.get("food_text", "").strip()
        uploaded_file = request.FILES.get("food_file")
        if uploaded_file and not text:
            suffix = uploaded_file.name.lower().rsplit(".", 1)[-1] if "." in uploaded_file.name else ""
            if suffix not in {"txt", "csv", "md"}:
                result = {"error": "仅支持 TXT、CSV 或 MD 文本文件。"}
            elif uploaded_file.size > 2 * 1024 * 1024:
                result = {"error": "文件不能超过 2 MB。"}
            else:
                raw = uploaded_file.read()
                try:
                    text = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    text = raw.decode("gb18030", errors="replace").strip()
        if text and result is None:
            text = text[:2000]
            model_name = get_default_model()
            ml.ensure_trained(model_name)
            try:
                pred = ml.predict(text, model_name)
            except FileNotFoundError as e:
                result = {"error": str(e)}
            else:
                pred["confidence_pct"] = pred["confidence"] * 100
                pred["path_items"] = [item.strip() for item in pred["path"].split("/")]
                for item in pred["top_k"]:
                    item["confidence_pct"] = item["confidence"] * 100
                rec = PredictionRecord.objects.create(
                    input_text=text[:500], predicted_code=pred["predicted_code"],
                    predicted_name=pred["predicted_name"], confidence=pred["confidence"],
                    model_name=model_name, user=request.user,
                )
                result = {"text": text, "record": rec, "pred": pred}
        elif result is None:
            result = {"error": "请输入食品名称、品类描述，或上传文本格式的食品成分表。", "text": text}
    # 基础数据展示：各级分类数量 + 一级类目占比
    l1_list = FoodCategory.objects.filter(level=1)
    total_records = PredictionRecord.objects.count()
    # 按一级类目统计推理记录
    dist = []
    for c in l1_list:
        code_prefix = c.code + "-"
        cnt = PredictionRecord.objects.filter(predicted_code__startswith=code_prefix).count()
        if cnt > 0:
            dist.append({"name": c.name, "count": cnt})
    ctx = {
        "result": result,
        "l1_count": FoodCategory.objects.filter(level=1).count(),
        "l2_count": FoodCategory.objects.filter(level=2).count(),
        "l3_count": FoodCategory.objects.filter(level=3).count(),
        "sample_count": FoodSample.objects.count(),
        "total_records": total_records,
        "dist": dist,
        "role": get_role(request.user),
        "default_model": get_default_model(),
    }
    return render(request, "classifier/demo_home.html", ctx)


# ---------------- 后台 ----------------
@admin_required
def admin_dashboard(request):
    ctx = {
        "l1": FoodCategory.objects.filter(level=1).count(),
        "l2": FoodCategory.objects.filter(level=2).count(),
        "l3": FoodCategory.objects.filter(level=3).count(),
        "samples": FoodSample.objects.count(),
        "records": PredictionRecord.objects.count(),
        "users": User.objects.count(),
        "models": ml.list_models(),
        "logs": OperationLog.objects.all()[:10],
        "default_model": get_default_model(),
    }
    return render(request, "classifier/admin_dashboard.html", ctx)


@admin_required
def category_list(request):
    cats = FoodCategory.objects.all()
    ctx = paginated_context(request, cats, 25)
    ctx["cats"] = ctx["page_obj"]
    return render(request, "classifier/category_list.html", ctx)


@admin_required
def category_add(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        name = request.POST.get("name", "").strip()
        level = int(request.POST.get("level", 3))
        parent = request.POST.get("parent_code", "").strip() or None
        if code and name:
            FoodCategory.objects.update_or_create(
                code=code, defaults={"name": name, "level": level, "parent_code": parent}
            )
            log_op(request, "品类管理", f"新增/更新类目 {code} {name}")
            messages.success(request, f"类目“{name}”已保存。")
        else:
            messages.warning(request, "分类编码和类目名称不能为空。")
        return redirect("category_list")
    parents = FoodCategory.objects.filter(level__in=[1, 2])
    return render(request, "classifier/category_form.html", {"parents": parents})


@admin_required
def category_delete(request, pk):
    cat = get_object_or_404(FoodCategory, pk=pk)
    if request.method == "POST":
        log_op(request, "品类管理", f"删除类目 {cat.code} {cat.name}")
        category_name = cat.name
        cat.delete()
        messages.success(request, f"类目“{category_name}”已删除。")
    return redirect("category_list")


@admin_required
def sample_list(request):
    samples = FoodSample.objects.select_related("category").all()
    q = request.GET.get("q", "").strip()
    if q:
        samples = samples.filter(name__icontains=q)
    ctx = paginated_context(request, samples, 30)
    ctx.update({"samples": ctx["page_obj"], "q": q})
    return render(request, "classifier/sample_list.html", ctx)


@admin_required
def sample_add(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        desc = request.POST.get("desc", "").strip()
        code = request.POST.get("category", "").strip()
        if name and code:
            cat = get_object_or_404(FoodCategory, pk=code)
            FoodSample.objects.create(
                name=name, description=desc, category=cat,
                source="user", created_by=request.user,
            )
            log_op(request, "样本管理", f"新增样本 {name} -> {code}")
            messages.success(request, f"样本“{name}”已加入数据集。")
        else:
            messages.warning(request, "食品名称和三级类目不能为空。")
        return redirect("sample_list")
    cats = FoodCategory.objects.filter(level=3)
    return render(request, "classifier/sample_form.html", {"cats": cats})


@admin_required
def model_manager(request):
    models = ml.list_models()
    default = get_default_model()
    return render(request, "classifier/model_manager.html",
                  {"models": models, "default": default})


@admin_required
def model_train(request, name):
    if name in ("svm", "rf"):
        meta = ml.train(name)
        log_op(request, "模型管理", f"重新训练 {name}，准确率 {meta['accuracy']:.4f}")
        messages.success(request, f"{name.upper()} 训练完成，测试准确率 {meta['accuracy'] * 100:.1f}%。")
    return redirect("model_manager")


@admin_required
def record_list(request):
    records = PredictionRecord.objects.select_related("user").all()
    model_filter = request.GET.get("model", "").strip()
    if model_filter:
        records = records.filter(model_name=model_filter)
    ctx = paginated_context(request, records, 30)
    ctx.update({"records": ctx["page_obj"], "model_filter": model_filter})
    return render(request, "classifier/record_list.html", ctx)


@admin_required
def record_export(request):
    import csv
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=food_classify_records.csv"
    writer = csv.writer(response)
    writer.writerow(["时间", "输入文本", "预测类目", "置信度", "使用模型", "操作人"])
    for r in PredictionRecord.objects.all():
        writer.writerow([
            r.created_at.strftime("%Y-%m-%d %H:%M:%S"), r.input_text,
            f"{r.predicted_name}({r.predicted_code})", f"{r.confidence:.4f}",
            r.model_name, r.user.username if r.user else "",
        ])
    log_op(request, "记录管理", "导出分类记录 CSV")
    return response


@admin_required
def user_manager(request):
    users = User.objects.select_related("profile").all()
    return render(request, "classifier/user_manager.html", {"users": users})


@admin_required
def user_role(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        role = request.POST.get("role", "student")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        log_op(request, "权限管理", f"设置 {user.username} 角色为 {role}")
        messages.success(request, f"用户“{user.username}”的角色已更新。")
    return redirect("user_manager")


@admin_required
def model_set_default(request, name):
    if name in ("svm", "rf"):
        SiteConfig.objects.update_or_create(key="default_model", defaults={"value": name})
        log_op(request, "模型管理", f"将默认推理模型设为 {name}")
        messages.success(request, f"已将 {name.upper()} 设为默认推理模型。")
    return redirect("model_manager")

from django.db import models
from django.contrib.auth.models import User


class FoodCategory(models.Model):
    """三级食品类目。code 形如 01 / 01-01 / 01-01-01。"""

    LEVEL_CHOICES = [(1, "一级类目"), (2, "二级类目"), (3, "三级类目")]
    code = models.CharField("分类编码", max_length=32, primary_key=True)
    name = models.CharField("类目名称", max_length=64)
    level = models.IntegerField("层级", choices=LEVEL_CHOICES)
    parent_code = models.CharField("父级编码", max_length=32, null=True, blank=True)

    class Meta:
        verbose_name = "食品类目"
        verbose_name_plural = "食品类目"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name}({self.code})"

    def full_path(self):
        names = []
        cur = self
        while cur is not None:
            names.insert(0, cur.name)
            if cur.parent_code:
                try:
                    cur = FoodCategory.objects.get(pk=cur.parent_code)
                except FoodCategory.DoesNotExist:
                    cur = None
            else:
                cur = None
        return " / ".join(names)


class FoodSample(models.Model):
    SOURCE_CHOICES = [("seed", "内置种子数据"), ("user", "用户上传")]
    name = models.CharField("食品名称", max_length=128)
    description = models.TextField("品类描述", blank=True)
    category = models.ForeignKey(
        FoodCategory, on_delete=models.CASCADE, verbose_name="所属三级类目"
    )
    source = models.CharField("数据来源", max_length=16, choices=SOURCE_CHOICES, default="seed")
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="创建人"
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "食品样本"
        verbose_name_plural = "食品样本"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} -> {self.category.code}"


class PredictionRecord(models.Model):
    input_text = models.TextField("输入文本")
    predicted_code = models.CharField("预测类目编码", max_length=32)
    predicted_name = models.CharField("预测类目名称", max_length=64)
    confidence = models.FloatField("置信度")
    model_name = models.CharField("使用模型", max_length=32)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="操作人"
    )
    created_at = models.DateTimeField("推理时间", auto_now_add=True)

    class Meta:
        verbose_name = "分类推理记录"
        verbose_name_plural = "分类推理记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.input_text[:20]} -> {self.predicted_name}({self.confidence:.2f})"


class VisionDetectionRecord(models.Model):
    STATUS_CHOICES = [("completed", "检测完成"), ("failed", "检测失败")]

    image = models.ImageField("原始图片", upload_to="vision/originals/%Y/%m/%d")
    annotated_image = models.ImageField(
        "标注结果图", upload_to="vision/annotated/%Y/%m/%d", blank=True
    )
    status = models.CharField(
        "检测状态", max_length=16, choices=STATUS_CHOICES, default="completed"
    )
    has_defect = models.BooleanField("是否存在缺陷", default=False)
    primary_class = models.CharField("主要缺陷类型", max_length=64, blank=True)
    confidence = models.FloatField("最高置信度", default=0)
    detections = models.JSONField("检测框明细", default=list, blank=True)
    inference_ms = models.FloatField("推理耗时（毫秒）", default=0)
    model_name = models.CharField("使用模型", max_length=64, default="YOLOv8n")
    threshold = models.FloatField("置信度阈值", default=0.25)
    error_message = models.TextField("失败原因", blank=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="操作人"
    )
    created_at = models.DateTimeField("检测时间", auto_now_add=True)

    class Meta:
        verbose_name = "包装缺陷检测记录"
        verbose_name_plural = "包装缺陷检测记录"
        ordering = ["-created_at"]

    def __str__(self):
        result = self.primary_class or ("合格" if self.status == "completed" else "失败")
        return f"{self.image.name} -> {result}"


class UserProfile(models.Model):
    ROLE_CHOICES = [("student", "实训学生"), ("admin", "后台管理员")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField("角色", max_length=16, choices=ROLE_CHOICES, default="student")

    class Meta:
        verbose_name = "用户角色"
        verbose_name_plural = "用户角色"

    def __str__(self):
        return f"{self.user.username}({self.get_role_display()})"


class SiteConfig(models.Model):
    """站点配置：当前默认推理模型等。单例。"""

    key = models.CharField("配置键", max_length=32, primary_key=True)
    value = models.CharField("配置值", max_length=64)

    class Meta:
        verbose_name = "站点配置"
        verbose_name_plural = "站点配置"

    def __str__(self):
        return f"{self.key}={self.value}"


class OperationLog(models.Model):
    """后台操作日志（满足文档"操作日志基础记录"要求）。"""

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="操作人"
    )
    action = models.CharField("操作类型", max_length=64)
    detail = models.TextField("操作详情", blank=True)
    created_at = models.DateTimeField("时间", auto_now_add=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("classifier", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="VisionDetectionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="vision/originals/%Y/%m/%d", verbose_name="原始图片")),
                ("annotated_image", models.ImageField(blank=True, upload_to="vision/annotated/%Y/%m/%d", verbose_name="标注结果图")),
                ("status", models.CharField(choices=[("completed", "检测完成"), ("failed", "检测失败")], default="completed", max_length=16, verbose_name="检测状态")),
                ("has_defect", models.BooleanField(default=False, verbose_name="是否存在缺陷")),
                ("primary_class", models.CharField(blank=True, max_length=64, verbose_name="主要缺陷类型")),
                ("confidence", models.FloatField(default=0, verbose_name="最高置信度")),
                ("detections", models.JSONField(blank=True, default=list, verbose_name="检测框明细")),
                ("inference_ms", models.FloatField(default=0, verbose_name="推理耗时（毫秒）")),
                ("model_name", models.CharField(default="YOLOv8n", max_length=64, verbose_name="使用模型")),
                ("threshold", models.FloatField(default=0.25, verbose_name="置信度阈值")),
                ("error_message", models.TextField(blank=True, verbose_name="失败原因")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="检测时间")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name="操作人")),
            ],
            options={
                "verbose_name": "包装缺陷检测记录",
                "verbose_name_plural": "包装缺陷检测记录",
                "ordering": ["-created_at"],
            },
        ),
    ]

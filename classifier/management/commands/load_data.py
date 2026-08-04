# -*- coding: utf-8 -*-
"""数据初始化：把 dataset.json 灌入数据库，并创建演示账号。

用法：
    python manage.py load_data
"""
import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from classifier.models import (
    FoodCategory, FoodSample, UserProfile, SiteConfig,
)

DATASET = Path(__file__).resolve().parents[2] / "ml" / "dataset.json"


class Command(BaseCommand):
    help = "加载食品分类数据集并创建演示账号"

    def handle(self, *args, **opts):
        data = json.loads(DATASET.read_text(encoding="utf-8"))

        # 1) 类目
        cat_count = 0
        for c in data["categories"]:
            obj, created = FoodCategory.objects.update_or_create(
                code=c["code"],
                defaults={"name": c["name"], "level": c["level"], "parent_code": c["parent"]},
            )
            if created:
                cat_count += 1
        self.stdout.write(self.style.SUCCESS(f"类目就绪：{FoodCategory.objects.count()} 条（新增 {cat_count}）"))

        # 2) 样本（仅在内置数据为空时导入，避免重复）
        if FoodSample.objects.filter(source="seed").exists():
            self.stdout.write("种子样本已存在，跳过。")
        else:
            cat_map = {c.code: c for c in FoodCategory.objects.all()}
            objs = []
            for s in data["samples"]:
                objs.append(FoodSample(
                    name=s["name"], description=s["desc"],
                    category=cat_map[s["code"]], source="seed",
                ))
            FoodSample.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f"种子样本导入：{len(objs)} 条"))

        # 3) 默认模型配置
        SiteConfig.objects.update_or_create(key="default_model", defaults={"value": "svm"})

        # 4) 演示账号
        for username, role, pwd in [
            ("student", "student", "student123"),
            ("admin", "admin", "admin123"),
        ]:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(pwd)
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            self.stdout.write(self.style.SUCCESS(f"账号 {username}/{pwd}（{role}）就绪"))

        self.stdout.write(self.style.SUCCESS("数据初始化完成。"))

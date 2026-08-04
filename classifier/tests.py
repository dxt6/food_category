from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import FoodCategory, PredictionRecord, UserProfile


class FrontendFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="student_test", password="student123")
        UserProfile.objects.create(user=self.student, role="student")
        self.admin = User.objects.create_user(username="admin_test", password="admin123")
        UserProfile.objects.create(user=self.admin, role="admin")

    @staticmethod
    def prediction():
        return {
            "model_name": "svm",
            "predicted_code": "01-01-01",
            "predicted_name": "膨化食品",
            "predicted_level": 3,
            "confidence": 0.826,
            "path": "休闲食品 / 膨化食品 / 薯片",
            "top_k": [
                {"code": "01-01-01", "name": "膨化食品", "confidence": 0.826},
                {"code": "01-02-01", "name": "饼干", "confidence": 0.112},
                {"code": "01-03-01", "name": "坚果", "confidence": 0.062},
            ],
        }

    @patch("classifier.views.ml.predict")
    @patch("classifier.views.ml.ensure_trained")
    def test_text_prediction_builds_display_values(self, ensure_trained, predict):
        predict.return_value = self.prediction()
        self.client.force_login(self.student)

        response = self.client.post(reverse("demo_home"), {"food_text": "原味马铃薯片"})

        self.assertEqual(response.status_code, 200)
        result = response.context["result"]
        self.assertEqual(result["pred"]["confidence_pct"], 82.6)
        self.assertEqual(result["pred"]["path_items"], ["休闲食品", "膨化食品", "薯片"])
        self.assertEqual(PredictionRecord.objects.count(), 1)

    @patch("classifier.views.ml.predict")
    @patch("classifier.views.ml.ensure_trained")
    def test_text_file_can_drive_prediction(self, ensure_trained, predict):
        predict.return_value = self.prediction()
        self.client.force_login(self.student)
        upload = SimpleUploadedFile("ingredients.txt", "低温发酵酸奶".encode("utf-8"), content_type="text/plain")

        response = self.client.post(reverse("demo_home"), {"food_file": upload})

        self.assertEqual(response.status_code, 200)
        predict.assert_called_once_with("低温发酵酸奶", "svm")

    def test_unsupported_file_shows_real_error(self):
        self.client.force_login(self.student)
        upload = SimpleUploadedFile("ingredients.xlsx", b"not-a-workbook")

        response = self.client.post(reverse("demo_home"), {"food_file": upload})

        self.assertContains(response, "仅支持 TXT、CSV 或 MD 文本文件")
        self.assertEqual(PredictionRecord.objects.count(), 0)

    def test_admin_role_is_visible_on_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "管理员")

    def test_category_save_redirects_with_feedback(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("category_add"),
            {"code": "09", "name": "测试类目", "level": "1", "parent_code": ""},
            follow=True,
        )

        self.assertRedirects(response, reverse("category_list"))
        self.assertContains(response, "类目“测试类目”已保存")
        self.assertTrue(FoodCategory.objects.filter(pk="09").exists())

    def test_admin_pages_render_for_admin(self):
        self.client.force_login(self.admin)
        page_names = [
            "admin_dashboard", "category_list", "category_add", "sample_list",
            "sample_add", "model_manager", "record_list", "user_manager",
        ]

        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)

    def test_category_list_is_paginated(self):
        FoodCategory.objects.bulk_create([
            FoodCategory(code=f"{index:02d}", name=f"类目{index}", level=1)
            for index in range(1, 27)
        ])
        self.client.force_login(self.admin)

        response = self.client.get(reverse("category_list"))

        self.assertEqual(len(response.context["page_obj"]), 25)
        self.assertContains(response, "下一页")

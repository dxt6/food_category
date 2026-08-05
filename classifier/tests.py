import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import FoodCategory, PredictionRecord, UserProfile, VisionDetectionRecord
from .vision.dataset import prepare_dataset


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


class VisionFlowTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.student = User.objects.create_user(username="vision_student", password="student123")
        UserProfile.objects.create(user=self.student, role="student")
        self.admin = User.objects.create_user(username="vision_admin", password="admin123")
        UserProfile.objects.create(user=self.admin, role="admin")

    def tearDown(self):
        self.settings_override.disable()
        self.media_dir.cleanup()

    @staticmethod
    def image_upload(name="package.jpg"):
        buffer = io.BytesIO()
        Image.new("RGB", (96, 72), color=(220, 210, 190)).save(buffer, format="JPEG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")

    @staticmethod
    def prediction():
        return {
            "has_defect": True,
            "primary_class": "stain",
            "primary_display_name": "表面污渍",
            "confidence": 0.91,
            "confidence_pct": 91,
            "detections": [
                {
                    "class_id": 0,
                    "class_name": "stain",
                    "display_name": "表面污渍",
                    "confidence": 0.91,
                    "confidence_pct": 91,
                    "box": [10, 12, 60, 54],
                }
            ],
            "inference_ms": 48.2,
            "model_name": "YOLOv8n",
        }

    @patch("classifier.views.vision_dataset.source_summary", return_value={"total_images": 4056, "warnings": []})
    @patch("classifier.views.vision_pipeline.run_detection")
    def test_image_detection_creates_record(self, run_detection, source_summary):
        run_detection.return_value = self.prediction()
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("vision_demo"),
            {"package_image": self.image_upload(), "threshold": "0.25"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "发现包装缺陷")
        record = VisionDetectionRecord.objects.get()
        self.assertTrue(record.has_defect)
        self.assertEqual(record.primary_class, "stain")
        self.assertEqual(len(record.detections), 1)

    @patch("classifier.views.vision_dataset.source_summary", return_value={"total_images": 4056, "warnings": []})
    def test_invalid_image_is_rejected(self, source_summary):
        self.client.force_login(self.student)
        upload = SimpleUploadedFile("package.jpg", b"not-an-image", content_type="image/jpeg")

        response = self.client.post(reverse("vision_demo"), {"package_image": upload})

        self.assertContains(response, "图片无法读取")
        self.assertEqual(VisionDetectionRecord.objects.count(), 0)

    @patch("classifier.views.vision_dataset.source_summary", return_value={"total_images": 4056, "warnings": []})
    def test_vision_admin_pages_and_export(self, source_summary):
        self.client.force_login(self.admin)

        records_response = self.client.get(reverse("vision_record_list"))
        model_response = self.client.get(reverse("vision_model_manager"))
        export_response = self.client.get(reverse("vision_record_export"))

        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(model_response.status_code, 200)
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])


class VisionDatasetTests(TestCase):
    def test_prepare_dataset_remaps_boxes_and_creates_weak_labels(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as parent_dir:
            images_root = Path(source_dir) / "images"
            for class_name in ("normal", "stain", "seal_abnormal"):
                material_dir = images_root / class_name / "plastic"
                material_dir.mkdir(parents=True)
                for index in range(2):
                    image_path = material_dir / f"{class_name}_{index}.jpg"
                    Image.new("RGB", (48, 48), color=(index * 20, 100, 150)).save(image_path)
                    if class_name == "stain":
                        image_path.with_suffix(".txt").write_text(
                            "1 0.500000 0.500000 0.250000 0.250000\n", encoding="utf-8"
                        )
            output_dir = Path(parent_dir) / "prepared"

            manifest = prepare_dataset(source_dir, output_dir, val_ratio=0.5, seed=7)

            self.assertEqual(manifest["stats"]["splits"], {"train": 3, "val": 3})
            self.assertEqual(manifest["stats"]["weak_labels"], 2)
            stain_labels = list(output_dir.rglob("stain__plastic*.txt"))
            seal_labels = list(output_dir.rglob("seal_abnormal__plastic*.txt"))
            normal_labels = list(output_dir.rglob("normal__plastic*.txt"))
            self.assertTrue(all(path.read_text(encoding="utf-8").startswith("0 ") for path in stain_labels))
            self.assertTrue(all(path.read_text(encoding="utf-8").startswith("2 ") for path in seal_labels))
            self.assertTrue(all(not path.read_text(encoding="utf-8") for path in normal_labels))
            self.assertIn("nc: 4", (output_dir / "data.yaml").read_text(encoding="utf-8"))

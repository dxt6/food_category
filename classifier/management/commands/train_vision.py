import json
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from classifier.vision.dataset import prepare_dataset


class Command(BaseCommand):
    help = "训练食品包装缺陷 YOLOv8n 模型，并安装最佳权重供网站推理使用。"

    def add_arguments(self, parser):
        parser.add_argument("--epochs", type=int, default=30)
        parser.add_argument("--imgsz", type=int, default=640)
        parser.add_argument("--batch", type=int, default=8)
        parser.add_argument("--device", default="auto")
        parser.add_argument("--workers", type=int, default=4)
        parser.add_argument("--base-model", default="yolov8n.pt")
        parser.add_argument("--name", default="food_package_yolov8n")
        parser.add_argument("--force-prepare", action="store_true")

    def handle(self, *args, **options):
        data_yaml = Path(settings.VISION_PREPARED_DIR) / "data.yaml"
        if not data_yaml.exists() or options["force_prepare"]:
            self.stdout.write("正在准备标准 YOLO 数据集……")
            prepare_dataset(force=options["force_prepare"])

        try:
            import torch
            from ultralytics import YOLO
        except ImportError as error:
            raise CommandError("缺少 ultralytics/torch，请先使用 uv 安装 requirements.txt。") from error

        device = options["device"]
        if device == "auto":
            device = 0 if torch.cuda.is_available() else "cpu"
        self.stdout.write(f"训练设备：{device}；基础模型：{options['base_model']}")

        model = YOLO(options["base_model"])
        result = model.train(
            data=str(data_yaml),
            epochs=options["epochs"],
            imgsz=options["imgsz"],
            batch=options["batch"],
            device=device,
            workers=options["workers"],
            project=str(settings.VISION_RUNS_DIR),
            name=options["name"],
            patience=max(10, options["epochs"] // 3),
            plots=True,
            exist_ok=True,
        )
        best_path = Path(model.trainer.best)
        if not best_path.exists():
            raise CommandError(f"训练结束但未找到最佳权重：{best_path}")

        Path(settings.VISION_MODELS_DIR).mkdir(parents=True, exist_ok=True)
        shutil.copy2(best_path, settings.VISION_MODEL_PATH)
        metrics = {
            key: float(value)
            for key, value in (getattr(result, "results_dict", {}) or {}).items()
            if isinstance(value, (int, float))
        }
        def portable_path(path):
            resolved = Path(path).resolve()
            try:
                return resolved.relative_to(settings.BASE_DIR).as_posix()
            except ValueError:
                return str(resolved)

        metadata = {
            "trained_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "model_name": "YOLOv8n",
            "base_model": options["base_model"],
            "epochs": options["epochs"],
            "imgsz": options["imgsz"],
            "batch": options["batch"],
            "device": str(device),
            "data_yaml": portable_path(data_yaml),
            "run_dir": portable_path(model.trainer.save_dir),
            "metrics": metrics,
        }
        Path(settings.VISION_MODEL_META_PATH).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.stdout.write(self.style.SUCCESS(f"模型已安装：{settings.VISION_MODEL_PATH}"))

import json
from pathlib import Path

from django.conf import settings
from PIL import Image

from .dataset import DEFECT_LABELS_ZH


_cached_model = None
_cached_model_path = None


def model_status():
    model_path = Path(settings.VISION_MODEL_PATH)
    meta_path = Path(settings.VISION_MODEL_META_PATH)
    metadata = {}
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            metadata = {}
    raw_metrics = metadata.get("metrics", {})
    metrics = {
        "precision_pct": float(raw_metrics.get("metrics/precision(B)", 0)) * 100,
        "recall_pct": float(raw_metrics.get("metrics/recall(B)", 0)) * 100,
        "map50_pct": float(raw_metrics.get("metrics/mAP50(B)", 0)) * 100,
        "map5095_pct": float(raw_metrics.get("metrics/mAP50-95(B)", 0)) * 100,
    }
    return {
        "ready": model_path.exists(),
        "path": str(model_path),
        "size_mb": model_path.stat().st_size / 1024 / 1024 if model_path.exists() else 0,
        "modified_at": model_path.stat().st_mtime if model_path.exists() else None,
        "metadata": metadata,
        "metrics": metrics,
        "device": settings.VISION_DEVICE,
    }


def reset_model_cache():
    global _cached_model, _cached_model_path
    _cached_model = None
    _cached_model_path = None


def _load_model():
    global _cached_model, _cached_model_path
    model_path = Path(settings.VISION_MODEL_PATH)
    if not model_path.exists():
        raise FileNotFoundError(
            "尚未找到包装缺陷检测模型，请由管理员先准备数据并执行 train_vision 训练命令。"
        )
    if _cached_model is None or _cached_model_path != str(model_path):
        from ultralytics import YOLO

        _cached_model = YOLO(str(model_path))
        _cached_model_path = str(model_path)
    return _cached_model


def run_detection(image_path, output_path, confidence=0.25):
    model = _load_model()
    predict_options = {
        "source": str(image_path),
        "conf": float(confidence),
        "verbose": False,
    }
    if settings.VISION_DEVICE not in {"", "auto"}:
        predict_options["device"] = settings.VISION_DEVICE
    results = model.predict(**predict_options)
    if not results:
        raise RuntimeError("模型没有返回推理结果。")

    result = results[0]
    detections = []
    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls.item())
            class_name = str(result.names[class_id])
            coordinates = [round(float(value), 1) for value in box.xyxy[0].tolist()]
            score = float(box.conf.item())
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "display_name": DEFECT_LABELS_ZH.get(class_name, class_name),
                    "confidence": score,
                    "confidence_pct": score * 100,
                    "box": coordinates,
                }
            )

    detections.sort(key=lambda item: item["confidence"], reverse=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotted = result.plot(labels=True, conf=True, line_width=3)
    Image.fromarray(plotted[:, :, ::-1]).save(output_path, quality=92)
    inference_ms = sum(float(value) for value in (result.speed or {}).values())
    primary = detections[0] if detections else None
    return {
        "has_defect": bool(detections),
        "primary_class": primary["class_name"] if primary else "",
        "primary_display_name": primary["display_name"] if primary else "包装合格",
        "confidence": primary["confidence"] if primary else 0,
        "confidence_pct": primary["confidence_pct"] if primary else 0,
        "detections": detections,
        "inference_ms": inference_ms,
        "model_name": "YOLOv8n",
    }

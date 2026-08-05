import hashlib
import json
import os
import random
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from django.conf import settings


DEFECT_CLASSES = ("stain", "printing_error", "seal_abnormal", "bulge_leakage")
DEFECT_LABELS_ZH = {
    "stain": "表面污渍",
    "printing_error": "印刷错误",
    "seal_abnormal": "封口异常",
    "bulge_leakage": "胀气漏液",
}
SOURCE_CLASS_IDS = {
    "normal": 0,
    "stain": 1,
    "printing_error": 2,
    "seal_abnormal": 3,
    "bulge_leakage": 4,
}
TARGET_CLASS_IDS = {name: index for index, name in enumerate(DEFECT_CLASSES)}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _source_images(source_root):
    images_root = Path(source_root) / "images"
    if not images_root.exists():
        raise FileNotFoundError(f"找不到视觉数据目录：{images_root}")
    return [
        path
        for path in images_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]


def source_summary(source_root=None):
    source_root = Path(source_root or settings.VISION_DATASET_ROOT)
    images_root = source_root / "images"
    class_counts = Counter()
    material_counts = Counter()
    labeled_images = 0
    box_count = 0
    weak_label_candidates = 0

    for image_path in _source_images(source_root):
        relative = image_path.relative_to(images_root)
        class_name = relative.parts[0] if relative.parts else "unknown"
        material = relative.parts[1] if len(relative.parts) > 2 else "未归档"
        class_counts[class_name] += 1
        material_counts[material] += 1
        label_path = image_path.with_suffix(".txt")
        label_text = label_path.read_text(encoding="utf-8").strip() if label_path.exists() else ""
        if label_text:
            labeled_images += 1
            box_count += len([line for line in label_text.splitlines() if line.strip()])
        elif class_name in DEFECT_CLASSES:
            weak_label_candidates += 1

    total_images = sum(class_counts.values())
    defect_images = sum(class_counts[name] for name in DEFECT_CLASSES)
    warnings = []
    if len(DEFECT_CLASSES) < 6:
        warnings.append("当前仅有 4 类缺陷，尚缺包装破损、标签错位等类别，未达到指标中的 6 类要求。")
    if weak_label_candidates:
        warnings.append(
            f"{weak_label_candidates} 张缺陷图缺少局部框，准备训练集时会生成整图弱标注。"
        )

    return {
        "source_root": str(source_root),
        "total_images": total_images,
        "defect_images": defect_images,
        "normal_images": class_counts["normal"],
        "defect_ratio": defect_images / total_images if total_images else 0,
        "labeled_images": labeled_images,
        "box_count": box_count,
        "weak_label_candidates": weak_label_candidates,
        "class_counts": dict(sorted(class_counts.items())),
        "material_counts": dict(sorted(material_counts.items())),
        "warnings": warnings,
    }


def _stable_seed(seed, group_name):
    digest = hashlib.sha256(f"{seed}:{group_name}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _safe_stem(relative_path):
    joined = "__".join(relative_path.with_suffix("").parts)
    safe = re.sub(r"[^0-9A-Za-z_-]+", "_", joined).strip("_") or "image"
    if len(safe) > 150:
        digest = hashlib.sha1(str(relative_path).encode("utf-8")).hexdigest()[:12]
        safe = f"{safe[:136]}_{digest}"
    return safe


def _link_or_copy(source, destination):
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def _remap_label(label_text, fallback_class_name):
    remapped = []
    for line in label_text.splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        try:
            source_class_id = int(float(parts[0]))
        except ValueError:
            continue
        source_name = next(
            (name for name, class_id in SOURCE_CLASS_IDS.items() if class_id == source_class_id),
            fallback_class_name,
        )
        if source_name not in TARGET_CLASS_IDS:
            continue
        remapped.append(" ".join([str(TARGET_CLASS_IDS[source_name]), *parts[1:]]))
    return "\n".join(remapped)


def prepare_dataset(
    source_root=None,
    output_root=None,
    val_ratio=0.2,
    seed=42,
    force=False,
    balance_train=True,
):
    source_root = Path(source_root or settings.VISION_DATASET_ROOT).resolve()
    output_root = Path(output_root or settings.VISION_PREPARED_DIR).resolve()
    marker_path = output_root / ".vision-prepared"
    manifest_path = output_root / "manifest.json"

    if output_root.exists():
        if not force and manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        if not marker_path.exists():
            raise ValueError(f"拒绝覆盖非本工具生成的目录：{output_root}")
        shutil.rmtree(output_root)

    if output_root == source_root or source_root in output_root.parents:
        raise ValueError("训练输出目录不能覆盖或位于原始数据目录内。")

    images_root = source_root / "images"
    grouped = {}
    for image_path in _source_images(source_root):
        relative = image_path.relative_to(images_root)
        class_name = relative.parts[0]
        if class_name not in SOURCE_CLASS_IDS:
            continue
        material = relative.parts[1] if len(relative.parts) > 2 else "未归档"
        grouped.setdefault((class_name, material), []).append(image_path)

    split_items = {"train": [], "val": []}
    for group, paths in sorted(grouped.items()):
        paths = sorted(paths)
        random.Random(_stable_seed(seed, "/".join(group))).shuffle(paths)
        val_count = 0 if len(paths) < 2 else max(1, min(len(paths) - 1, round(len(paths) * val_ratio)))
        split_items["val"].extend(paths[:val_count])
        split_items["train"].extend(paths[val_count:])

    for split_name in split_items:
        (output_root / split_name / "images").mkdir(parents=True, exist_ok=True)
        (output_root / split_name / "labels").mkdir(parents=True, exist_ok=True)

    stats = {
        "splits": {"train": 0, "val": 0},
        "classes": Counter(),
        "train_classes": Counter(),
        "val_classes": Counter(),
        "existing_labels": 0,
        "weak_labels": 0,
        "negative_samples": 0,
        "balanced_samples": 0,
        "hardlinks": 0,
        "copies": 0,
        "boxes": 0,
    }
    train_outputs = defaultdict(list)

    for split_name, paths in split_items.items():
        for image_path in paths:
            relative = image_path.relative_to(images_root)
            class_name = relative.parts[0]
            destination_stem = _safe_stem(relative)
            destination_image = output_root / split_name / "images" / f"{destination_stem}{image_path.suffix.lower()}"
            destination_label = output_root / split_name / "labels" / f"{destination_stem}.txt"
            transfer_mode = _link_or_copy(image_path, destination_image)
            stats["hardlinks" if transfer_mode == "hardlink" else "copies"] += 1

            source_label = image_path.with_suffix(".txt")
            source_text = source_label.read_text(encoding="utf-8").strip() if source_label.exists() else ""
            if class_name == "normal":
                label_text = ""
                stats["negative_samples"] += 1
            else:
                label_text = _remap_label(source_text, class_name) if source_text else ""
                if label_text:
                    stats["existing_labels"] += 1
                else:
                    target_id = TARGET_CLASS_IDS[class_name]
                    label_text = f"{target_id} 0.500000 0.500000 0.960000 0.960000"
                    stats["weak_labels"] += 1
                stats["boxes"] += len(label_text.splitlines())
            destination_label.write_text(label_text + ("\n" if label_text else ""), encoding="utf-8")
            stats["splits"][split_name] += 1
            stats["classes"][class_name] += 1
            stats[f"{split_name}_classes"][class_name] += 1
            if split_name == "train" and class_name in DEFECT_CLASSES:
                train_outputs[class_name].append((destination_image, destination_label))

    if balance_train and train_outputs:
        target_count = max(len(items) for items in train_outputs.values())
        for class_name in DEFECT_CLASSES:
            items = train_outputs.get(class_name, [])
            if not items:
                continue
            deficit = target_count - len(items)
            for index in range(deficit):
                source_image, source_label = items[index % len(items)]
                balanced_stem = f"{source_image.stem}__balance{index:04d}"
                destination_image = source_image.with_name(balanced_stem + source_image.suffix)
                destination_label = source_label.with_name(balanced_stem + ".txt")
                transfer_mode = _link_or_copy(source_image, destination_image)
                stats["hardlinks" if transfer_mode == "hardlink" else "copies"] += 1
                shutil.copy2(source_label, destination_label)
                stats["splits"]["train"] += 1
                stats["train_classes"][class_name] += 1
                stats["balanced_samples"] += 1

    yaml_text = "\n".join(
        [
            f"path: {output_root.as_posix()}",
            "train: train/images",
            "val: val/images",
            f"nc: {len(DEFECT_CLASSES)}",
            "names:",
            *[f"  {index}: {name}" for index, name in enumerate(DEFECT_CLASSES)],
            "",
        ]
    )
    (output_root / "data.yaml").write_text(yaml_text, encoding="utf-8")
    marker_path.write_text("食品包装缺陷 YOLO 训练集\n", encoding="utf-8")

    summary = source_summary(source_root)
    manifest = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": summary,
        "output_root": str(output_root),
        "data_yaml": str(output_root / "data.yaml"),
        "val_ratio": val_ratio,
        "seed": seed,
        "target_classes": list(DEFECT_CLASSES),
        "target_labels_zh": DEFECT_LABELS_ZH,
        "stats": {
            **stats,
            "classes": dict(sorted(stats["classes"].items())),
            "train_classes": dict(sorted(stats["train_classes"].items())),
            "val_classes": dict(sorted(stats["val_classes"].items())),
        },
        "balance_train": balance_train,
        "annotation_policy": {
            "normal": "空标签负样本",
            "existing_boxes": "重映射原 YOLO 框标注",
            "missing_defect_boxes": "整图 96% 范围弱标注",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest

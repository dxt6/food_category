# -*- coding: utf-8 -*-
"""轻量化食品文本分类管线：TF-IDF + {SVM / 随机森林}。

- 模型可切换（满足文档"模型简易切换"要求）
- 预测返回 三级类目 + 一级/二级路径 + 置信度
"""
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

MODELS_DIR = Path(__file__).resolve().parent / "models"
DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"

MODEL_BUILDERS = {
    "svm": lambda: SVC(probability=True, kernel="linear", C=1.0),
    "rf": lambda: RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
}


def load_dataset():
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    samples = data["samples"]
    # 文本 = 食品名称 + 品类描述；标签 = 三级类目编码
    texts = [f"{s['name']} {s['desc']}" for s in samples]
    labels = [s["code"] for s in samples]
    return texts, labels


def _build_category_index():
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cat_by_code = {c["code"]: c for c in data["categories"]}
    return cat_by_code


def train(model_name="svm", test_size=0.2):
    """训练并保存模型，返回评测指标。"""
    if model_name not in MODEL_BUILDERS:
        raise ValueError(f"不支持的模型: {model_name}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    texts, labels = load_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=test_size, random_state=42, stratify=labels
    )
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1, max_features=40000)
    Xtr = vec.fit_transform(X_train)
    Xte = vec.transform(X_test)
    clf = MODEL_BUILDERS[model_name]()
    clf.fit(Xtr, y_train)
    y_pred = clf.predict(Xte)
    acc = accuracy_score(y_test, y_pred)

    bundle = {
        "model_name": model_name,
        "vectorizer": vec,
        "clf": clf,
        "category_index": _build_category_index(),
        "accuracy": float(acc),
    }
    model_path = MODELS_DIR / f"{model_name}.joblib"
    joblib.dump(bundle, model_path)

    # 保存可读元信息
    meta = {
        "model_name": model_name,
        "accuracy": float(acc),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "n_classes": len(set(labels)),
        "report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
    }
    (MODELS_DIR / f"{model_name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def _load_bundle(model_name):
    model_path = MODELS_DIR / f"{model_name}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"模型 {model_name} 未训练，请先执行训练。")
    return joblib.load(model_path)


def predict(text, model_name="svm", top_k=3):
    """对单条文本分类，返回预测结果与置信度。"""
    bundle = _load_bundle(model_name)
    vec = bundle["vectorizer"]
    clf = bundle["clf"]
    cat_idx = bundle["category_index"]

    X = vec.transform([text])
    proba = clf.predict_proba(X)[0]
    classes = clf.classes_
    order = proba.argsort()[::-1][:top_k]
    top = []
    for i in order:
        code = classes[i]
        cat = cat_idx.get(code, {})
        path = _path_of(cat_idx, code)
        top.append({
            "code": code,
            "name": cat.get("name", code),
            "level": cat.get("level", 3),
            "confidence": float(proba[i]),
            "path": path,
        })
    best = top[0]
    return {
        "model_name": model_name,
        "predicted_code": best["code"],
        "predicted_name": best["name"],
        "predicted_level": best["level"],
        "confidence": best["confidence"],
        "path": best["path"],
        "top_k": top,
    }


def _path_of(cat_idx, code):
    names = []
    cur = cat_idx.get(code)
    while cur is not None:
        names.insert(0, cur["name"])
        parent = cur.get("parent")
        cur = cat_idx.get(parent) if parent else None
    return " / ".join(names)


def list_models():
    """列出已训练模型及其准确率。"""
    result = []
    for p in sorted(MODELS_DIR.glob("*.meta.json")):
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
            result.append(meta)
        except Exception:
            continue
    return result


def ensure_trained(model_name="svm"):
    """若模型不存在则自动训练，方便一键演示。"""
    model_path = MODELS_DIR / f"{model_name}.joblib"
    if not model_path.exists():
        return train(model_name)
    return None


if __name__ == "__main__":
    for m in ["svm", "rf"]:
        print(f"== 训练 {m} ==")
        print(train(m))

"""
Visión por computadora — análisis de imágenes:
detección facial, edad, género, emoción usando DeepFace + OpenCV.
"""

import os
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("ocr_spatial")

_face_cascade = None


def _load_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        cv2_dir = os.path.dirname(cv2.__file__)
        path = os.path.join(cv2_dir, "data", "haarcascade_frontalface_default.xml")
        _face_cascade = cv2.CascadeClassifier(path)
    return _face_cascade


def _is_false_positive(bbox: dict, img_width: int, img_height: int) -> bool:
    face_area = bbox.get("w", 0) * bbox.get("h", 0)
    img_area = img_width * img_height
    if img_area == 0:
        return True
    ratio = face_area / img_area
    is_tiny = ratio < 0.02
    is_huge = ratio > 0.60
    if is_tiny:
        logger.debug("Falso positivo: rostro muy pequeño (%.1f%%)", ratio * 100)
    if is_huge:
        logger.debug("Falso positivo: rostro cubre toda la imagen (%.1f%%)", ratio * 100)
    return is_tiny or is_huge


def analyze_image(image_path: str) -> dict:
    result = {
        "faces_detected": 0,
        "faces": [],
        "error": None,
    }

    img = cv2.imread(image_path)
    if img is None:
        result["error"] = "No se pudo leer la imagen"
        return result

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = img.shape[:2]
    result["image_size"] = f"{width}x{height}"

    face_cascade = _load_face_cascade()
    raw_faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    for x, y, w, h in raw_faces:
        bbox = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        if _is_false_positive(bbox, width, height):
            continue
        face_info = {"index": len(result["faces"]), "bbox": bbox}

        face_roi_gray = gray[y : y + h, x : x + w]

        smile_cascade = cv2.CascadeClassifier(
            os.path.join(os.path.dirname(cv2.__file__), "data", "haarcascade_smile.xml")
        )
        smiles = smile_cascade.detectMultiScale(
            face_roi_gray, scaleFactor=1.7, minNeighbors=22, minSize=(25, 25)
        )
        face_info["smiling"] = len(smiles) > 0

        result["faces"].append(face_info)

    result["faces_detected"] = len(result["faces"])

    deepface_result = _analyze_deepface(image_path)
    if deepface_result:
        filtered_df = [
            df for df in deepface_result.get("faces", [])
            if not _is_false_positive(df.get("bbox", {}), width, height)
        ]
        if not result["faces"] and filtered_df:
            result["faces"] = filtered_df
            result["faces_detected"] = len(filtered_df)
        else:
            for i, df in enumerate(filtered_df):
                if i < len(result["faces"]):
                    result["faces"][i].update(df)

    return result


def _analyze_deepface(image_path: str) -> Optional[dict]:
    try:
        from deepface import DeepFace
    except ImportError:
        return None

    try:
        objs = DeepFace.analyze(
            img_path=image_path,
            actions=["age", "gender", "emotion"],
            enforce_detection=False,
            silent=True,
        )
        if not objs:
            return None
        if not isinstance(objs, list):
            objs = [objs]

        faces = []
        for obj in objs:
            region = obj.get("region", {})
            face = {
                "index": len(faces),
                "bbox": {"x": region.get("x", 0), "y": region.get("y", 0),
                         "w": region.get("w", 0), "h": region.get("h", 0)},
                "gender": obj.get("dominant_gender", "unknown"),
                "age": obj.get("age"),
                "age_range": _age_to_range(obj.get("age")),
                "emotion": obj.get("dominant_emotion", "unknown"),
                "emotion_scores": obj.get("emotion", {}),
                "smiling": obj.get("dominant_emotion") in ("happy", "surprise"),
                "confidence": obj.get("face_confidence"),
            }
            faces.append(face)

        return {"faces_detected": len(faces), "faces": faces}

    except Exception as e:
        logger.warning("Error en DeepFace: %s", e)
        return None


def _age_to_range(age: Optional[int]) -> str:
    if age is None:
        return "desconocido"
    if age < 3:
        return "0-2"
    elif age < 8:
        return "4-6"
    elif age < 15:
        return "8-12"
    elif age < 25:
        return "15-24"
    elif age < 38:
        return "25-37"
    elif age < 48:
        return "38-47"
    elif age < 60:
        return "48-59"
    else:
        return "60+"


def describe_vision(result: dict) -> str:
    parts = []
    n = result["faces_detected"]
    if n == 0:
        parts.append("No se detectaron rostros en la imagen.")
        return "\n".join(parts)

    parts.append(f"Se detectaron {n} rostro(s):")
    for f in result["faces"]:
        desc = f"  - Rostro #{f['index'] + 1}:"
        gender = f.get("gender", "desconocido")
        age = f.get("age")
        age_str = f"{age} anos" if age is not None else "desconocida"
        desc += f" {gender}, edad ~{age_str}"
        emotion = f.get("emotion", "desconocida")
        desc += f", emocion: {emotion}"
        if f.get("smiling"):
            desc += " [SONRIENDO]"
        parts.append(desc)

    return "\n".join(parts)

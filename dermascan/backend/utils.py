"""
utils.py
Image pre-processing helpers shared by training and inference.
"""

import numpy as np
import cv2
from PIL import Image

IMG_SIZE = 224


def read_image_from_bytes(file_bytes: bytes) -> np.ndarray:
    """Decode uploaded file bytes into an RGB numpy array."""
    pil_img = Image.open(file_bytes).convert("RGB")
    return np.array(pil_img)


def preprocess_image(img_array: np.ndarray) -> np.ndarray:
    """
    Resize + light denoising with OpenCV, then shape into a model-ready
    batch of one image. Pixel scaling for MobileNetV2 happens inside the
    model itself (see model.py), so this only handles geometry/cleanup.
    """
    img = cv2.resize(img_array, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
    img = cv2.bilateralFilter(img, d=5, sigmaColor=40, sigmaSpace=40)  # mild denoise, keeps edges
    img = img.astype("float32")
    return np.expand_dims(img, axis=0)  # shape: (1, 224, 224, 3)

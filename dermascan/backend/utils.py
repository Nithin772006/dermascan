"""
utils.py
Image pre-processing helpers shared by training and inference.
"""

import numpy as np
from PIL import Image, ImageFilter

try:
    import cv2
except ImportError:
    cv2 = None

IMG_SIZE = 224


def read_image_from_bytes(file_bytes: bytes) -> np.ndarray:
    """Decode uploaded file bytes into an RGB numpy array."""
    pil_img = Image.open(file_bytes).convert("RGB")
    return np.array(pil_img)


def preprocess_image(img_array: np.ndarray) -> np.ndarray:
    """
    Resize + light denoising, then shape into a model-ready
    batch of one image. Falls back smoothly to Pillow if OpenCV is not installed
    (e.g., in lean serverless environments like Vercel).
    """
    if cv2 is not None:
        img = cv2.resize(img_array, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
        img = cv2.bilateralFilter(img, d=5, sigmaColor=40, sigmaSpace=40)  # mild denoise, keeps edges
    else:
        # High-quality Pillow fallback without system C/GL dependencies
        pil_img = Image.fromarray(img_array.astype("uint8")).resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)
        pil_img = pil_img.filter(ImageFilter.SMOOTH_MORE)
        img = np.array(pil_img)

    img = img.astype("float32")
    return np.expand_dims(img, axis=0)  # shape: (1, 224, 224, 3)


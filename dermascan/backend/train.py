"""
train.py
Trains the DermaScan skin disease classification model on the HAM10000 dataset
loaded via kagglehub using transfer learning with MobileNetV2.

Dataset: kmader/skin-cancer-mnist-ham10000
Classes:
  0 - Actinic Keratosis (akiec)
  1 - Basal Cell Carcinoma (bcc)
  2 - Benign Keratosis (bkl)
  3 - Dermatofibroma (df)
  4 - Melanocytic Nevi (nv)
  5 - Vascular Lesion (vasc)
  6 - Melanoma (mel)

Saves the trained model to:
  dermascan/backend/skin_model.h5
"""

import os
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import zipfile
import io
import time
import numpy as np
import pandas as pd
import cv2
import kagglehub
from kagglehub import KaggleDatasetAdapter

import tensorflow as tf
from tensorflow.keras import layers, models, utils

from model import CLASS_NAMES, HAM10000_CODES, IMG_SIZE

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_H5_PATH = os.path.join(BACKEND_DIR, "skin_model.h5")
MODEL_KERAS_PATH = os.path.join(BACKEND_DIR, "skin_model.keras")


def load_ham10000_data():
    """
    Downloads / loads HAM10000 pixel dataset using kagglehub.
    Handles direct CSV or zip-wrapped CSV formats.
    """
    print("[1/5] Loading HAM10000 dataset via kagglehub...")
    dataset_handle = "kmader/skin-cancer-mnist-ham10000"
    file_path = "hmnist_28_28_RGB.csv"

    # Attempt to load with KaggleDatasetAdapter.PANDAS
    try:
        df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            dataset_handle,
            file_path,
        )
        print("Dataset loaded successfully via KaggleDatasetAdapter.PANDAS.")
    except Exception as e:
        print(f"KaggleDatasetAdapter returned: {e}. Resolving cached zip file directly...")
        cache_dir = kagglehub.config.get_cache_folder()
        candidates = []
        for root, _, files in os.walk(cache_dir):
            if "hmnist_28_28_RGB.csv" in files:
                candidates.append(os.path.join(root, "hmnist_28_28_RGB.csv"))

        if not candidates:
            # Force download
            download_path = kagglehub.dataset_download(dataset_handle)
            for root, _, files in os.walk(download_path):
                if "hmnist_28_28_RGB.csv" in files:
                    candidates.append(os.path.join(root, "hmnist_28_28_RGB.csv"))

        raw_path = candidates[0]
        # Check if it's a zip file
        with open(raw_path, "rb") as f:
            magic = f.read(4)
        if magic.startswith(b"PK"):
            with zipfile.ZipFile(raw_path) as z:
                csv_name = z.namelist()[0]
                df = pd.read_csv(z.open(csv_name))
        else:
            df = pd.read_csv(raw_path)

    print(f"Dataset shape: {df.shape}")
    print("Label distribution in raw data:")
    for label_id in sorted(df["label"].unique()):
        code = HAM10000_CODES[label_id]
        name = CLASS_NAMES[label_id]
        count = (df["label"] == label_id).sum()
        print(f"  [{label_id}] {code} ({name}): {count} samples")

    return df


def prepare_balanced_dataset(df: pd.DataFrame, max_per_class: int = 250):
    """
    Balances classes to avoid heavy bias toward majority class (nv = 67%),
    reshapes 28x28x3 pixels, and resizes to 224x224 for MobileNetV2.
    """
    print(f"\n[2/5] Creating balanced dataset (target ~{max_per_class} per class)...")
    np.random.seed(42)

    balanced_dfs = []
    for label_id in range(len(CLASS_NAMES)):
        sub_df = df[df["label"] == label_id]
        n_samples = len(sub_df)
        if n_samples >= max_per_class:
            sampled = sub_df.sample(n=max_per_class, random_state=42)
        else:
            # Oversample minority classes
            multiplier = int(np.ceil(max_per_class / n_samples))
            oversampled = pd.concat([sub_df] * multiplier, ignore_index=True)
            sampled = oversampled.sample(n=max_per_class, random_state=42)
        balanced_dfs.append(sampled)

    balanced_df = pd.concat(balanced_dfs, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    print(f"Balanced dataset size: {len(balanced_df)} samples ({len(CLASS_NAMES)} classes x {max_per_class})")

    # Extract pixel data and labels
    feature_cols = [c for c in balanced_df.columns if c != "label"]
    pixel_data = balanced_df[feature_cols].values.astype(np.uint8)
    labels = balanced_df["label"].values

    # Reshape from (N, 2352) to (N, 28, 28, 3)
    images_28 = pixel_data.reshape(-1, 28, 28, 3)

    print(f"Resizing images from 28x28 to {IMG_SIZE}x{IMG_SIZE} for MobileNetV2...")
    images_224 = np.zeros((len(images_28), IMG_SIZE, IMG_SIZE, 3), dtype=np.float32)
    for i in range(len(images_28)):
        # Linear resize to 224x224
        resized = cv2.resize(images_28[i], (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
        images_224[i] = resized

    # Split train / validation (80% / 20%)
    split_idx = int(0.80 * len(images_224))
    x_train, x_val = images_224[:split_idx], images_224[split_idx:]
    y_train, y_val = labels[:split_idx], labels[split_idx:]

    y_train_cat = utils.to_categorical(y_train, num_classes=len(CLASS_NAMES))
    y_val_cat = utils.to_categorical(y_val, num_classes=len(CLASS_NAMES))

    print(f"Train split: {len(x_train)} images | Val split: {len(x_val)} images")
    return x_train, y_train_cat, x_val, y_val_cat


def train_and_save_model(x_train, y_train, x_val, y_val):
    """
    Builds MobileNetV2 transfer learning model, extracts features,
    trains the dense classification head, builds the end-to-end model,
    and saves to skin_model.h5.
    """
    print("\n[3/5] Initializing MobileNetV2 base with ImageNet weights...")
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = False

    # Extract features using frozen base (fast on CPU)
    print("Extracting feature embeddings from train images...")
    t0 = time.time()
    x_train_prep = tf.keras.applications.mobilenet_v2.preprocess_input(x_train.copy())
    x_val_prep = tf.keras.applications.mobilenet_v2.preprocess_input(x_val.copy())

    feat_train = base_model.predict(x_train_prep, batch_size=32, verbose=1)
    feat_val = base_model.predict(x_val_prep, batch_size=32, verbose=1)
    print(f"Features extracted in {time.time() - t0:.1f}s. Feature shape: {feat_train.shape[1:]}")

    print("\n[4/5] Training classification head...")
    head_input = layers.Input(shape=feat_train.shape[1:])
    h = layers.GlobalAveragePooling2D()(head_input)
    h = layers.Dense(128, activation="relu")(h)
    h = layers.Dropout(0.3)(h)
    head_output = layers.Dense(len(CLASS_NAMES), activation="softmax")(h)

    head_model = models.Model(head_input, head_output, name="classification_head")
    head_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    epochs = 15
    batch_size = 32
    history = head_model.fit(
        feat_train,
        y_train,
        validation_data=(feat_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        verbose=1,
    )

    val_acc = history.history["val_accuracy"][-1]
    print(f"\nFinal Validation Accuracy: {val_acc * 100:.2f}%")

    print("\n[5/5] Assembling end-to-end MobileNetV2 model and saving...")
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="image_input")
    x = layers.Rescaling(1.0 / 127.5, offset=-1.0)(inputs)
    x = base_model(x, training=False)
    # Transfer trained head layers
    x = head_model.layers[1](x)  # GAP
    x = head_model.layers[2](x)  # Dense 128
    x = head_model.layers[3](x)  # Dropout
    outputs = head_model.layers[4](x)  # Dense 7 Softmax

    full_model = models.Model(inputs, outputs, name="dermascan_cnn")
    full_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    # Save to skin_model.h5
    full_model.save(MODEL_H5_PATH)
    print(f"[SUCCESS] Saved model to {MODEL_H5_PATH} ({os.path.getsize(MODEL_H5_PATH) / (1024*1024):.1f} MB)")

    # Also save .keras
    try:
        full_model.save(MODEL_KERAS_PATH)
        print(f"[SUCCESS] Saved model to {MODEL_KERAS_PATH}")
    except Exception as e:
        print(f"Note: .keras save skipped ({e})")

    # Quick test inference
    sample = np.expand_dims(x_val[0], axis=0)
    pred_probs = full_model.predict(sample, verbose=0)[0]
    top_class_idx = int(np.argmax(pred_probs))
    print(f"\nSanity check inference on sample image:")
    print(f"  Predicted condition: {CLASS_NAMES[top_class_idx]} ({pred_probs[top_class_idx]*100:.1f}% confidence)")
    print("  Full probability breakdown:")
    for i, name in enumerate(CLASS_NAMES):
        print(f"    - {name}: {pred_probs[i]*100:.1f}%")

    return full_model


if __name__ == "__main__":
    print("=" * 60)
    print(" DermaScan AI - Model Training Pipeline (HAM10000)")
    print("=" * 60)
    df = load_ham10000_data()
    x_train, y_train, x_val, y_val = prepare_balanced_dataset(df, max_per_class=250)
    train_and_save_model(x_train, y_train, x_val, y_val)
    print("\nTraining complete! Restart dermascan/backend/app.py to run in trained model mode.")

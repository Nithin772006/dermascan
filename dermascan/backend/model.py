"""
model.py
Defines the CNN architecture used for skin disease classification.

Approach: transfer learning on MobileNetV2 (pretrained on ImageNet).
Training a CNN completely from scratch needs a very large dataset to
generalize well; transfer learning gets solid accuracy on a dataset the
size of HAM10000 with far less training time - a good choice for a
college/internship project as well as a practical one.
"""

try:
    import tensorflow as tf
    from tensorflow.keras import layers, models
except ImportError:
    tf = None
    layers = None
    models = None

IMG_SIZE = 224
CLASS_NAMES = [
    "Actinic Keratosis",
    "Basal Cell Carcinoma",
    "Benign Keratosis",
    "Dermatofibroma",
    "Melanocytic Nevi",
    "Vascular Lesion",
    "Melanoma",
]
HAM10000_CODES = ["akiec", "bcc", "bkl", "df", "nv", "vasc", "mel"]
HAM10000_TO_CLASS = dict(zip(HAM10000_CODES, CLASS_NAMES))


def build_model(num_classes: int = len(CLASS_NAMES), fine_tune: bool = False):
    """
    Builds and returns the classification model.
    """
    if tf is None:
        raise RuntimeError("TensorFlow is required to build or train the model, but is not installed.")
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )
    base_model.trainable = fine_tune

    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = layers.Rescaling(1.0 / 127.5, offset=-1.0)(inputs)
    x = base_model(x, training=fine_tune)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = models.Model(inputs, outputs, name="dermascan_cnn")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


if __name__ == "__main__":
    if tf is not None:
        m = build_model()
        m.summary()
    else:
        print("[DermaScan] TensorFlow not installed. Running in mock/development mode.")

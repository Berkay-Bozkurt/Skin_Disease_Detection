import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.layers import Conv2D, AveragePooling2D, Flatten, Dense, concatenate, Input, Dropout
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.applications.densenet import DenseNet121
from tensorflow.keras.applications.mobilenet import MobileNet
from tensorflow.keras import backend as K
from tensorflow import keras
def load_data(csv_path, image_dir):
    # Load CSV data
    df = pd.read_csv(csv_path)
    X = np.array(df.drop(["diagnostic", "img_id"], axis=1))
    y = np.array(df["diagnostic"])
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y)
    y = to_categorical(y)

    # Load images using ImageDataGenerator
    datagen = ImageDataGenerator(preprocessing_function=preprocess_input)
    batch_size = 600
    target_size = (224, 224)
    class_mode = 'categorical'

    train_generator = datagen.flow_from_dataframe(
        dataframe=df,
        directory=image_dir,
        x_col="img_id",
        y_col="diagnostic",
        target_size=target_size,
        batch_size=batch_size,
        class_mode=class_mode,
        shuffle=True
    )

    xtrain, ytrain = next(train_generator)
    return xtrain, ytrain, X, y
def build_cnn_model(input_shape):
    BASE_MODEL = ResNet50(
        weights='imagenet',
        include_top=False,
        pooling='avg',
        input_shape=input_shape
    )
    BASE_MODEL.trainable = False

    model = Sequential()
    model.add(BASE_MODEL)
    model.add(Dense(units=2048, activation="elu"))
    model.add(Dense(units=512, activation="elu"))
    model.add(Dense(units=128, activation="elu"))
    model.add(Dropout(rate=0.5))
    return model

def build_ann_model(input_shape):
    model = Sequential()
    input_ann = Input(shape=input_shape)
    ann_output = Dense(units=16, activation='elu')(input_ann)
    model.add(Dropout(rate=0.5))
    model = Model(inputs=input_ann, outputs=ann_output)
    return model

def build_combined_model(cnn_model, ann_model):
    concatenated = concatenate([cnn_model.output, ann_model.output])
    combined_output = Dense(units=32, activation='elu')(concatenated)
    combined_output = Dense(units=16, activation='elu')(combined_output)
    combined_output = Dense(units=8, activation='elu')(combined_output)
    combined_output = Dense(units=6, activation='softmax')(combined_output)

    combined_model = Model(
        inputs=[cnn_model.input, ann_model.input],
        outputs=[combined_output]
    )
    return combined_model

def train_model(model, xtrain, ytrain, X, y, batch_size=48, epochs=1_000):
    opt = tf.keras.optimizers.SGD(lr=0.001)
    model.compile(optimizer=opt, loss=tf.keras.losses.CategoricalCrossentropy(), metrics=[tf.keras.metrics.CategoricalAccuracy()])
    
    stop_early = tf.keras.callbacks.EarlyStopping(monitor='val_categorical_accuracy', patience=50)
    
    history = model.fit([xtrain, X], ytrain, batch_size=batch_size, epochs=epochs,
                        callbacks=[stop_early], validation_split=0.2)
    
    return history

# Clear Keras session
K.clear_session()

# Load and preprocess the data
csv_path = "Augmentation/train_df.csv"
image_dir = "cancer/images/train"
xtrain, ytrain, X, y = load_data(csv_path, image_dir)
# Build individual models
cnn_model = build_cnn_model(input_shape=(224, 224, 3))
ann_model = build_ann_model(input_shape=X.shape[1])
# Build combined model
combined_model = build_combined_model(cnn_model, ann_model)
combined_model.summary()
# Train the model
history = train_model(combined_model, xtrain, ytrain, X, y, batch_size=48, epochs=1_000)
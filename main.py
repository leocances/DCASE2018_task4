import os

import keras.utils
from keras.layers import Reshape, BatchNormalization, Activation, MaxPooling2D, Conv2D, Dropout, GRU, Dense, \
    Input, Bidirectional, TimeDistributed, GlobalAveragePooling1D
from keras.models import Model

import Normalizer
import Metrics
import CallBacks
from datasetGenerator import DCASE2018

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--normalizer", help="normalizer [file_MinMax | global_MinMax | file_Mean | global_Mean |"
                                             " file_standard | global_standard")
    parser.add_argument("--output_model", help="basename for save file of the model")

    args = parser.parse_args()

    normalizer = None
    if args.normalizer:
        if args.normalizer == "file_MinMax": normalizer = Normalizer.File_MinMaxNormalization
        if args.normalizer == "global_MinMax": normalizer = Normalizer.Global_MinMaxNormalization
        if args.normalizer == "file_Mean": normalizer = Normalizer.File_MeanNormalization
        if args.normalizer == "global_Mean": normalizer = Normalizer.Global_MeanNormalization
        if args.normalizer == "file_Standard": normalizer = Normalizer.File_Standardization
        if args.normalizer == "global_Standard": normalizer = Normalizer.Global_Stadardization
        if args.normalizer == "unit": normalizer = Normalizer.UnitLength


    dataset = DCASE2018(
        meta_train_weak="meta/weak.csv",
        feat_train_weak="/homeLocal/eriador/Documents/DCASE2018/task4/features/train/weak/mel",
        #meta_train_unlabelOutDomain="meta/unlabel_out_of_domain.csv",
        #feat_train_unlabelOutDomain="/homeLocal/eriador/Documents/DCASE2018/task4/features/train/unlabel_out_of_domain/mel",
        normalizer=normalizer
    )

    # ==================================================================================================================
    #   Creating the model
    # ==================================================================================================================
    kInput = Input(dataset.getInputShape())

    block1 = Conv2D(filters=64, kernel_size=(3, 3), padding="same")(kInput)
    block1 = BatchNormalization()(block1)
    block1 = Activation(activation="relu")(block1)
    block1 = MaxPooling2D(pool_size=(1, 4))(block1)
    block1 = Dropout(0.3)(block1)

    block2 = Conv2D(filters=64, kernel_size=(3, 3), padding="same")(block1)
    block2 = BatchNormalization()(block2)
    block2 = Activation(activation="relu")(block2)
    block2 = MaxPooling2D(pool_size=(1, 4))(block2)
    block2 = Dropout(0.3)(block2)

    block3 = Conv2D(filters=64, kernel_size=(3, 3), padding="same")(block2)
    block3 = BatchNormalization()(block3)
    block3 = Activation(activation="relu")(block3)
    block3 = MaxPooling2D(pool_size=(1, 4))(block3)
    block3 = Dropout(0.3)(block3)
    # block3 ndim = 4

    targetShape = dataset.originalShape[0]
    reshape = Reshape(target_shape=(targetShape, 64))(block3)
    # reshape ndim = 3

    gru = Bidirectional(
        GRU(kernel_initializer='glorot_uniform', recurrent_dropout=0.0, dropout=0.3, units=64, return_sequences=True)
    )(reshape)
    print(gru.shape)

    output = TimeDistributed(
        Dense(dataset.nbClass, activation="sigmoid"),
    )(gru)
    print(output.shape)

    output = GlobalAveragePooling1D()(output)

    model = Model(inputs=kInput, outputs=output)
    keras.utils.print_summary(model, line_length=100)

    # ======== model hyper parameters ========
    epochs = 100
    metrics = "binary_accuracy"
    loss = "binary_crossentropy"

    # compile model
    model.compile(loss=loss,
                  optimizer="adam",
                  metrics=[metrics, Metrics.precision, Metrics.recall, Metrics.f1])

    # fit
    model.fit(
        x=dataset.trainingDataset["input"],
        y=dataset.trainingDataset["output"],
        epochs=200,
        batch_size=8,
        validation_data=(
            dataset.validationDataset["input"],
            dataset.validationDataset["output"]
        ),
        callbacks=[CallBacks.MyProgbarLogger()],
        verbose=0
    )

    # save the model
    path = args.output_model
    if os.path.isfile(path):
        os.makedirs(path)

    # save json
    model_json = model.to_json()
    with open(os.path.join(path, "_json"), "w") as f:
        f.write(model_json)

    # save weight
    model.save_weights(os.path.join(path, "_weight"))



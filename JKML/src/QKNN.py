###############################################################################
###############################################################################
###############################################################################

import numpy as np
import pickle
from sklearn.neighbors import KNeighborsRegressor
from metric_learn import MLKR
from ase.atoms import Atoms
from typing import List, Tuple


def _generate_fchl(
    strs: List[Atoms], krr_cutoff: float, max_value: float = None
) -> Tuple[List[int], np.ndarray]:
    from qmllib.representations import generate_fchl18 as generate_representation

    repres = [None] * len(strs)
    max_atoms = max([len(strs.iloc[i].get_atomic_numbers()) for i in range(len(strs))])
    for i in range(len(repres)):
        repres[i] = generate_representation(
            strs.iloc[i].get_atomic_numbers(),
            strs.iloc[i].get_positions(),
            max_size=max_atoms,
            neighbors=max_atoms,
            cut_distance=krr_cutoff,
        )
    X_atoms = None
    X = np.array(repres)
    # flatten to 2D
    X = X.reshape(X.shape[0], -1)
    if np.isnan(X).any():
        raise ValueError("NaNs in FCHL representation!")
    # remove infinities TODO: is this good?
    if max_value is not None:
        X = np.minimum(X, max_value)
    return X_atoms, X


def _generate_mbdf(strs: List[Atoms], cutoff_r: float) -> List[List[int], np.ndarray]:
    from MBDF import generate_mbdf as generate_representation

    X_atoms = [strs[i].get_atomic_numbers() for i in range(len(strs))]
    X = generate_representation(
        np.array([i.get_atomic_numbers() for i in strs]),
        np.array([i.get_positions() for i in strs]),
        cutoff_r=cutoff_r,
        normalized=False,
        local=False,
    )
    return X_atoms, X


def calculate_representation(Qrepresentation, strs, krr_cutoff, max_value=1e6):
    match Qrepresentation:
        case "fchl":
            return _generate_fchl(strs, krr_cutoff, max_value)
        case "mbdf":
            return _generate_mbdf(strs, krr_cutoff)
        case _:
            raise NotImplementedError(
                f"Representation 'f{Qrepresentation}' not supported with the k-NN model!"
            )


def training(
    Qrepresentation,
    strs,
    Y_train,
    krr_cutoff,
    varsoutfile,
):

    ### REPRESENTATION CALCULATION ###
    X_atoms, X_train = calculate_representation(Qrepresentation, strs, krr_cutoff)

    # some info about the full representation
    print(
        "JKML(Q-kNN): Shape of the training representation: " + str(X_train.shape),
        flush=True,
    )
    print("JKML(Q-kNN): Training MLKR metric.", flush=True)
    # save train input files for off-site debugging
    with open(varsoutfile, "wb") as f:
        pickle.dump([X_train, Y_train], f)
        print(f"Saved pretrain vars to {str(f)}.", flush=True)
    mlkr = MLKR()
    mlkr.fit(X_train, Y_train)
    A = mlkr.get_mahalanobis_matrix()
    print("JKML(Q-kNN): Training k-NN regressor with MLKR metric.")
    knn = KNeighborsRegressor(metric=mlkr.get_metric())
    knn.fit(X_train, Y_train)
    print("JKML(Q-kNN): Training completed.", flush=True)
    knn_params = knn.get_params()
    knn_params["metric"] = "MLKR_placeholder"
    with open(varsoutfile, "wb") as f:
        pickle.dump([X_train, Y_train, X_atoms, A, mlkr, knn_params], f)
    return {
        key: value
        for key, value in locals().items()
        if key in ["X_train", "X_atoms", "A", "knn"]
    }


###############################################################################
###############################################################################
###############################################################################


def evaluate(Qrepresentation, krr_cutoff, X_train, strs, knn_model):

    import numpy as np

    ### REPRESENTATION CALCULATION ###
    _, X_test = calculate_representation(Qrepresentation, strs, krr_cutoff)

    # some info about the full representation
    print(
        "JKML(QML): Shape of the testing representation: " + str(X_test.shape),
        flush=True,
    )

    ### CORRECTING THE FCHL MATRIX SIZES
    # IF YOU ARE EXTENDING THIS WILL MAKE THE MATRIXES OF THE SAME SIZE
    if Qrepresentation == "fchl":
        if X_train.shape[1] != X_test.shape[1]:
            if X_train.shape[1] > X_test.shape[1]:
                small = X_test
                large = X_train
            else:
                small = X_train
                large = X_test
            newmatrix = np.zeros([small.shape[0], large.shape[1], 5, large.shape[3]])
            newmatrix[:, :, 0, :] = 1e100
            newmatrix[
                0 : small.shape[0], 0 : small.shape[1], 0:5, 0 : small.shape[3]
            ] = small
            if X_train.shape[1] > X_test.shape[1]:
                X_test = newmatrix
            else:
                X_train = newmatrix

    ### THE EVALUATION
    Y_predicted = knn_model.predict(X_test)
    Y_predicted = Y_predicted[None, :]
    return Y_predicted

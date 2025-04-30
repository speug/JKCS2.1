from .QKNN import calculate_representation
import pandas as pd
import numpy as np
from typing import Union
import os
from sklearn.metrics import pairwise_distances
from metric_learn import MLKR
import time
import pickle


class MLKRegressor:

    def __init__(
        self,
        n_components=None,
        init="auto",
        tol=None,
        max_iter=1000,
        verbose=False,
        preprocessor=None,
        random_state=None,
    ):
        self.n_components = n_components
        self.mlkr = MLKR(
            n_components, init, tol, max_iter, verbose, preprocessor, random_state
        )
        self.X_train = None
        self.Y_train = None
        self.n_train = None

    def gaussian_kernel(self, X_test):
        D = pairwise_distances(X_test, self.X_train, metric=self.mlkr.get_metric(), n_jobs=-1)
        return np.exp(-D)

    def fit(self, X_train, Y_train):
        self.mlkr.fit(X_train, Y_train)
        self.X_train = X_train
        self.Y_train = Y_train
        self.n_train = X_train.shape[0]

    def predict(self, X_test):
        K = self.gaussian_kernel(X_test)
        num = K @ self.Y_train
        denom = K.sum(axis=1)
        return num / denom


def load_hyperparams(hyper_cache: str):
    if hyper_cache is not None:
        with open(hyper_cache, "rb") as f:
            hyperparams: dict = pickle.load(f)
        print(f"JKML(Q-MLKR): Loaded hyperparameters from {hyper_cache}:", flush=True)
        if "representation" not in hyperparams:
            hyperparams["representation"] = {"cutoff": 8.0}
            print(
                f"JKML (Q-MLKR): Representation params not defined in hyperparams, use default value."
            )
        if "mlkr" not in hyperparams:
            hyperparams["mlkr"] = {"n_components": 50}
            print(
                f"JKML (Q-MLKR): knn params not defined in hyperparams, use default values."
            )
        print(hyperparams, flush=True)
    else:
        # use defaults
        hyperparams = {
            "mlkr": {"n_components": 50},
            "representation": {"cutoff": 8.0},
        }
        print(f"JKML(Q-MLKR): Using default hyperparams {hyperparams}", flush=True)
    return hyperparams


def training(
    Qrepresentation: str,
    strs: pd.Series,
    Y_train: np.ndarray,
    varsoutfile: Union[str, os.PathLike],
    hyper_cache=None,
):

    hyperparams = load_hyperparams(hyper_cache)
    # Convert structures to list to avoid indexing issues
    strs = strs.values

    ### REPRESENTATION CALCULATION ###
    repr_wall_start = time.perf_counter()
    repr_cpu_start = time.process_time()
    print(
        f"JKML(Q-MLKR): Calculating {Qrepresentation.upper()} representation.",
        flush=True,
    )
    X_atoms = [strs[i].get_atomic_numbers() for i in range(len(strs))]
    X_train = calculate_representation(
        Qrepresentation, strs, **hyperparams["representation"]
    )
    repr_train_wall = time.perf_counter() - repr_wall_start
    repr_train_cpu = time.process_time() - repr_cpu_start

    # some info about the full representation
    print(
        "JKML(Q-MLKR): Shape of the training representation: " + str(X_train.shape),
        flush=True,
    )
    # save train input files for off-site debugging
    with open(varsoutfile, "wb") as f:
        pickle.dump([X_train, Y_train], f)
        print(f"Saved pretrain vars to {str(f)}.", flush=True)
    train_wall_start = time.perf_counter()
    train_cpu_start = time.process_time()
    mlkr = MLKRegressor(**hyperparams["mlkr"])
    mlkr.fit(X_train, Y_train)
    train_wall = time.perf_counter() - train_wall_start
    train_cpu = time.process_time() - train_cpu_start
    A = mlkr.mlkr.get_mahalanobis_matrix()
    n_train, d_train = X_train.shape[0], np.sum(X_train.shape[1:])
    train_metadata = {
        "repr_train_wall": repr_train_wall,
        "repr_train_cpu": repr_train_cpu,
        "train_wall": train_wall,
        "train_cpu": train_cpu,
        "n_train": n_train,
        "d_train": d_train,
    }
    print("JKML(Q-MLKR): Training completed.", flush=True)
    with open(varsoutfile, "wb") as f:
        print(f"JKML(Q-MLKR): Saving training data to {varsoutfile}")
        pickle.dump(
            [
                X_train,
                Y_train,
                X_atoms,
                A,
                mlkr,
                train_metadata,
            ],
            f,
        )
    return {
        key: value
        for key, value in locals().items()
        if key
        in [
            "X_train",
            "X_atoms",
            "A",
            "mlkr",
            "repr_train_wall",
            "repr_train_cpu",
            "train_wall",
            "train_cpu",
            "n_train",
            "d_train",
        ]
    }


def evaluate(Qrepresentation, X_train, strs, mlkr_model, hyper_cache=None):

    import numpy as np

    hyperparams = load_hyperparams(hyper_cache)
    ### REPRESENTATION CALCULATION ###
    # Convert structures to list to avoid indexing issues
    for i, struct in enumerate(strs.values):
        assert struct == strs.iloc[i]
    strs = strs.values
    repr_wall_start = time.perf_counter()
    repr_cpu_start = time.process_time()
    X_test = calculate_representation(
        Qrepresentation, strs, **hyperparams["representation"]
    )
    print("JKML(k-NN): Calculate test kernel(s).", flush=True)
    repr_test_wall = time.perf_counter() - repr_wall_start
    repr_test_cpu = time.process_time() - repr_cpu_start

    # some info about the full representation
    print(
        "JKML(k-NN): Shape of the testing representation: " + str(X_test.shape),
        flush=True,
    )

    test_wall_start = time.perf_counter()
    test_cpu_start = time.process_time()
    Y_predicted = mlkr_model.predict(X_test)
    test_wall = time.perf_counter() - test_wall_start
    test_cpu = time.process_time() - test_cpu_start
    Y_predicted = Y_predicted[None, :]
    d_test = X_test.shape[1]
    return Y_predicted, repr_test_wall, repr_test_cpu, test_wall, test_cpu, d_test

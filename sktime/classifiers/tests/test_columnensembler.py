__author__ = 'Aaron Bostrom'

import numpy as np

from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import FunctionTransformer

from sktime.pipeline import FeatureUnion, Pipeline
from sktime.transformers.series_to_series import RandomIntervalSegmenter
from sktime.transformers.compose import RowwiseTransformer
from sktime.classifiers.time_series_neighbors import KNeighborsTimeSeriesClassifier as KNNTSC
from sktime.datasets.base import _load_dataset
from sktime.classifiers.dictionary_based.boss import BOSSEnsemble
from sktime.contrib.column_ensembler import ColumnEnsembleClassifier, HomogeneousColumnEnsembleClassifier


def test_univariate_column_ensembler():
    ct = ColumnEnsembleClassifier(
        [("KNN1", KNNTSC(n_neighbors=1), [1]),
         ("KNN2", KNNTSC(n_neighbors=1), [2])]
    )


def test_simple_column_ensembler():
    X_train, y_train = _load_dataset("JapaneseVowels", "TRAIN", True)
    X_test, y_test = _load_dataset("JapaneseVowels", "TEST", True)

    cts = HomogeneousColumnEnsembleClassifier(KNNTSC(n_neighbors=1))

    cts.fit(X_train, y_train)
    cts.score(X_test, y_test) == 1.0


def test_homogeneous_pipeline_column_ensmbler():
    X_train, y_train = _load_dataset("JapaneseVowels", "TRAIN", True)
    X_test, y_test = _load_dataset("JapaneseVowels", "TEST", True)

    ct = ColumnEnsembleClassifier(
        [("KNN%d " % i, KNNTSC(n_neighbors=1), [i]) for i in range(0, X_train.shape[1])]
    )

    ct.fit(X_train, y_train)
    ct.score(X_test, y_test)


def test_heterogenous_pipeline_column_ensmbler():
    X_train, y_train = _load_dataset("JapaneseVowels", "TRAIN", True)
    X_test, y_test = _load_dataset("JapaneseVowels", "TEST", True)

    n_intervals = 3

    steps = [
        ('segment', RandomIntervalSegmenter(n_intervals=n_intervals, check_input=False)),
        ('transform', FeatureUnion([
            ('mean', RowwiseTransformer(FunctionTransformer(func=np.mean, validate=False))),
            ('std', RowwiseTransformer(FunctionTransformer(func=np.std, validate=False)))
        ])),
        ('clf', DecisionTreeClassifier())
    ]
    clf1 = Pipeline(steps, random_state=1)

    # dims 0-3 with alternating classifiers.
    ct = ColumnEnsembleClassifier(
        [
            ("RandomIntervalTree", clf1, [0]),
            ("KNN4", KNNTSC(n_neighbors=1), [4]),
            ("BOSSEnsemble1 ", BOSSEnsemble(), [1]),
            ("KNN2", KNNTSC(n_neighbors=1), [2]),
            ("BOSSEnsemble3", BOSSEnsemble(), [3]),
        ]
    )

    ct.fit(X_train, y_train)
    ct.score(X_test, y_test)


if __name__ == "__main__":
    test_heterogenous_pipeline_column_ensmbler()

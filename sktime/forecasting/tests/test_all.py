#!/usr/bin/env python3 -u
# coding: utf-8

# test API provided through BaseForecaster

__author__ = ["Markus Löning"]
__all__ = [
    "test_clone",
    "test_not_fitted_error",
    "test_score",
    "test_predict_time_index",
    "test_update_predict_predicted_indices",
    "test_bad_y_input",
    "test_fit_non_stateful",
    "test_fit_update_set_params_returns_self",
    "test_fitted_params",
    "test_predict_in_sample",
    "test_predict_pred_interval",
    "test_update_predict_single",
]

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
from sktime.exceptions import NotFittedError
from sktime.forecasting.arima import AutoARIMA
from sktime.forecasting.model_selection import SlidingWindowSplitter
from sktime.forecasting.model_selection import temporal_train_test_split
from sktime.forecasting.tests import TEST_ALPHAS
from sktime.forecasting.tests import TEST_INS_FHS
from sktime.forecasting.tests import TEST_OOS_FHS
from sktime.forecasting.tests import TEST_STEP_LENGTHS
from sktime.forecasting.tests import TEST_WINDOW_LENGTHS
from sktime.forecasting.tests import TEST_YS
from sktime.performance_metrics.forecasting import smape_loss
from sktime.utils import all_estimators
from sktime.utils.testing.base import _construct_instance
from sktime.utils.testing.forecasting import assert_correct_pred_time_index
from sktime.utils.testing.forecasting import \
    compute_expected_index_from_update_predict
from sktime.utils.testing.forecasting import make_forecasting_problem
from sktime.utils.validation.forecasting import check_fh

# get all forecasters
FORECASTERS = [forecaster for (name, forecaster) in
               all_estimators(scitype="forecaster")]
FH0 = 1

# testing data
y_train, y_test = make_forecasting_problem()


@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_clone(Forecaster):
    f = _construct_instance(Forecaster)
    clone(f)


@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_fit_update_set_params_returns_self(Forecaster):
    f = _construct_instance(Forecaster)
    fitted_f = f.fit(y_train, FH0)
    assert fitted_f == f

    fitted_f = f.update(y_test, update_params=False)
    assert fitted_f == f

    fitted_f = f.set_params()
    assert fitted_f == f


@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_fit_non_stateful(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    a = f.predict()

    # refit without reconstructing
    f.fit(y_train, FH0)
    b = f.predict()
    np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_fitted_params(Forecaster):
    f = _construct_instance(Forecaster)
    f.fit(y_train, FH0)
    try:
        params = f.get_fitted_params()
        assert isinstance(params, dict)

    except NotImplementedError:
        pass


@pytest.mark.parametrize("Forecaster", FORECASTERS)
def test_not_fitted_error(Forecaster):
    f = _construct_instance(Forecaster)
    with pytest.raises(NotFittedError):
        f.predict(fh=1)

    with pytest.raises(NotFittedError):
        f.update(y_test, update_params=False)

    with pytest.raises(NotFittedError):
        cv = SlidingWindowSplitter(fh=1, window_length=1)
        f.update_predict(y_test, cv=cv)

    try:
        with pytest.raises(NotFittedError):
            f.get_fitted_params()
    except NotImplementedError:
        pass


def assert_correct_msg(exception, msg):
    assert exception.value.args[0] == msg


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("y", [
    np.random.random(size=3),  # array
    [1, 3, 0.5],  # list
    (1, 3, 0.5)  # tuple
])
def test_bad_y_input(Forecaster, y):
    expected_msg = f"`y` must be a pandas Series, but found type: {type(y)}"

    with pytest.raises(TypeError) as e:
        f = _construct_instance(Forecaster)
        f.fit(y, FH0)
    assert_correct_msg(e, expected_msg)


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("y_train", TEST_YS)
def test_predict_time_index(Forecaster, fh, y_train):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    y_pred = f.predict()
    assert_correct_pred_time_index(y_pred, y_train, fh)


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", TEST_INS_FHS)
@pytest.mark.parametrize("y_train", TEST_YS)
def test_predict_in_sample(Forecaster, fh, y_train):
    f = _construct_instance(Forecaster)
    try:
        f.fit(y_train, fh=fh)
        y_pred = f.predict()
        assert_correct_pred_time_index(y_pred, y_train, fh)
    except NotImplementedError:
        pass


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("y_train", TEST_YS)
def test_predict_in_sample_full(Forecaster, y_train):
    f = _construct_instance(Forecaster)

    # pmdarima, which we interface for AutoARIMA, fails when d > start where
    # start = 0 here for full in-sample predictions
    if isinstance(f, AutoARIMA):
        f.set_params(**{"max_D": 0})

    fh = -np.arange(len(y_train))  # full in-sample fh
    try:
        f.fit(y_train, fh=fh)
        y_pred = f.predict()
        assert_correct_pred_time_index(y_pred, y_train, fh)
    except NotImplementedError:
        pass


def check_pred_ints(pred_ints, y_train, y_pred, fh):
    # make iterable
    if isinstance(pred_ints, pd.DataFrame):
        pred_ints = [pred_ints]

    for pred_int in pred_ints:
        assert list(pred_int.columns) == ["lower", "upper"]
        assert_correct_pred_time_index(pred_int, y_train, fh)

        # check if errors are weakly monotonically increasing
        pred_errors = y_pred - pred_int["lower"]
        # assert pred_errors.is_mononotic_increasing
        assert np.all(
            pred_errors.values[1:].round(4) >= pred_errors.values[:-1].round(
                4))


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("alpha", TEST_ALPHAS)
def test_predict_pred_interval(Forecaster, fh, alpha):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh=fh)
    try:
        y_pred, pred_ints = f.predict(return_pred_int=True, alpha=alpha)
        check_pred_ints(pred_ints, y_train, y_pred, fh)

    except NotImplementedError:
        pass


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", TEST_OOS_FHS)
def test_score(Forecaster, fh):
    # compute expected score
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    y_pred = f.predict()

    fh_idx = check_fh(fh) - 1  # get zero based index
    expected = smape_loss(y_pred, y_test.iloc[fh_idx])

    # compare with actual score
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    actual = f.score(y_test.iloc[fh_idx], fh=fh)
    assert actual > 0
    assert actual == expected


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", TEST_OOS_FHS)
def test_update_predict_single(Forecaster, fh):
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    y_pred = f.update_predict_single(y_test)
    assert_correct_pred_time_index(y_pred, y_test, fh)


def check_update_predict_y_pred(y_pred, y_test, fh, step_length):
    assert isinstance(y_pred, (pd.Series, pd.DataFrame))
    if isinstance(y_pred, pd.DataFrame):
        assert y_pred.shape[1] > 1

    expected_index = compute_expected_index_from_update_predict(y_test, fh,
                                                                step_length)
    np.testing.assert_array_equal(y_pred.index, expected_index)


@pytest.mark.parametrize("Forecaster", FORECASTERS)
@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("window_length", TEST_WINDOW_LENGTHS)
@pytest.mark.parametrize("step_length", TEST_STEP_LENGTHS)
@pytest.mark.parametrize("y", TEST_YS)
def test_update_predict_predicted_indices(Forecaster, fh, window_length,
                                          step_length, y):
    y_train, y_test = temporal_train_test_split(y)
    cv = SlidingWindowSplitter(fh, window_length=window_length,
                               step_length=step_length)
    f = _construct_instance(Forecaster)
    f.fit(y_train, fh)
    try:
        y_pred = f.update_predict(y_test, cv=cv)
        check_update_predict_y_pred(y_pred, y_test, fh, step_length)
    except NotImplementedError:
        pass

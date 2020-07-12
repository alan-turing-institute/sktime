#!/usr/bin/env python3 -u
# coding: utf-8
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = "Markus Löning"

import numpy as np
import pandas as pd
import pytest
from sktime.forecasting.naive import NaiveForecaster
from sktime.forecasting.tests import TEST_OOS_FHS
from sktime.forecasting.tests import TEST_SPS
from sktime.forecasting.tests import TEST_WINDOW_LENGTHS
from sktime.utils.validation.forecasting import check_fh

n_timepoints = 30
n_train = 20
s = pd.Series(np.arange(n_timepoints))
y_train = s.iloc[:n_train]
y_test = s.iloc[n_train:]


@pytest.mark.parametrize("fh", TEST_OOS_FHS)
def test_strategy_last(fh):
    f = NaiveForecaster(strategy="last")
    f.fit(y_train)
    y_pred = f.predict(fh)
    expected = np.repeat(y_train.iloc[-1], len(f.fh))
    np.testing.assert_array_equal(y_pred, expected)


@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("window_length", TEST_WINDOW_LENGTHS)
def test_strategy_mean(fh, window_length):
    f = NaiveForecaster(strategy="mean", window_length=window_length)
    f.fit(y_train)
    y_pred = f.predict(fh)

    if window_length is None:
        window_length = len(y_train)

    expected = np.repeat(y_train.iloc[-window_length:].mean(), len(f.fh))
    np.testing.assert_array_equal(y_pred, expected)


@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("sp", TEST_SPS)
def test_strategy_seasonal_last(fh, sp):
    f = NaiveForecaster(strategy="last", sp=sp)
    f.fit(y_train)
    y_pred = f.predict(fh)

    # check predicted index
    np.testing.assert_array_equal(y_train.index[-1] + check_fh(fh),
                                  y_pred.index)
    # check values
    fh = check_fh(fh)  # get well formatted fh
    reps = np.int(np.ceil(max(fh) / sp))
    expected = np.tile(y_train.iloc[-sp:], reps=reps)[fh - 1]
    np.testing.assert_array_equal(y_pred, expected)


@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("sp", TEST_SPS)
@pytest.mark.parametrize("window_length", [*TEST_WINDOW_LENGTHS, None])
def test_strategy_seasonal_mean(fh, sp, window_length):
    if ((window_length is not None and window_length > sp) or
            (window_length is None)):
        f = NaiveForecaster(strategy="mean", sp=sp,
                            window_length=window_length)
        f.fit(y_train)
        y_pred = f.predict(fh)

        # check predicted index
        np.testing.assert_array_equal(y_train.index[-1] + check_fh(fh),
                                      y_pred.index)

        if window_length is None:
            window_length = len(y_train)

        # check values
        fh = check_fh(fh)  # get well formatted fh
        reps = np.int(np.ceil(max(fh) / sp))
        last_window = y_train.iloc[-window_length:].values.astype(float)
        last_window = np.pad(last_window,
                             (0, sp - len(last_window) % sp),
                             'constant',
                             constant_values=(-1))

        last_window = last_window.reshape(np.int(np.
                                                 ceil(len(last_window) /
                                                      sp)),
                                          sp)
        indices = np.where(last_window == -1)[-1]
        last_window[-1][indices] = \
            (last_window.sum(axis=0)[indices] +
             1) / (last_window.shape[-1] - 1)
        last_window = last_window.mean(axis=0)

        expected = np.tile(last_window, reps=reps)[fh - 1]
        np.testing.assert_array_equal(y_pred, expected)

@pytest.mark.parametrize("fh", TEST_OOS_FHS)
@pytest.mark.parametrize("window_length", TEST_WINDOW_LENGTHS)
def test_strategy_drift(fh, window_length):
    f = NaiveForecaster(strategy="drift", window_length=window_length)
    f.fit(y_train)
    y_pred = f.predict(fh)

    if window_length is None:
        window_length = len(y_train)

    window_length = y_train.iloc[-window_length:]
    drift = np.mean(np.diff(window_length))

    # get well formatted fh values
    fh = check_fh(fh)
    last_window = np.arange(window_length[-1],
                            window_length[-1] + \
                            drift * (max(fh) + 1),
                            drift)
    expected = last_window[fh - 1]
    np.testing.assert_array_equal(y_pred, expected)


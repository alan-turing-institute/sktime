#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__author__ = "Markus Löning"
__all__ = [
    "make_reduction",
    "ReducedTabularRegressorMixin",
    "ReducedTimeSeriesRegressorMixin",
    "DirectTimeSeriesRegressionForecaster",
    "RecursiveTimeSeriesRegressionForecaster",
    "DirectTabularRegressionForecaster",
    "RecursiveTabularRegressionForecaster",
    "MultioutputTabularRegressionForecaster",
    "ReducedForecaster",
]

import numpy as np
import pandas as pd
from sklearn.base import RegressorMixin
from sklearn.base import clone

from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.base._sktime import _BaseWindowForecaster
from sktime.forecasting.base._sktime import _OptionalForecastingHorizonMixin
from sktime.forecasting.base._sktime import _RequiredForecastingHorizonMixin
from sktime.forecasting.model_selection import SlidingWindowSplitter
from sktime.regression.base import BaseRegressor
from sktime.utils._maint import deprecated
from sktime.utils.validation import check_window_length
from sktime.utils.validation.forecasting import check_step_length
from sktime.utils.validation.forecasting import check_y


##############################################################################
# base classes for reduction from forecasting to regression


class BaseReducer(_BaseWindowForecaster):
    """Base class for reducing forecasting to time series regression"""

    _required_parameters = ["regressor"]

    def __init__(self, regressor, window_length=10, step_length=1):
        super(BaseReducer, self).__init__(window_length=window_length)
        self.regressor = regressor
        self.step_length = step_length
        self.step_length_ = None
        self._cv = None

    def _transform(self, y, X=None):
        """Transform data using rolling window approach"""
        if X is not None:
            raise NotImplementedError("Exogenous variables `X` are not yet supported.")
        y = check_y(y)

        # get integer time index
        cv = self._cv

        # Transform target series into tabular format using
        # rolling window tabularisation
        x_windows = []
        y_windows = []
        for x_index, y_index in cv.split(y):
            x_window = y.iloc[x_index]
            y_window = y.iloc[y_index]

            x_windows.append(x_window)
            y_windows.append(y_window)

        # Put into required input format for regression
        X, y = self._format_windows(x_windows, y_windows)
        return X, y

    def _format_windows(self, x_windows, y_windows=None):
        """Helper function to combine windows from temporal cross-validation
        into nested
        pd.DataFrame for reduction to time series regression or tabular
        np.array for
        tabular regression.

        Parameters
        ----------
        x_windows : list of pd.Series or np.array
        y_windows : list of pd.Series or np.array, optional (default=None)

        Returns
        -------
        X : pd.DataFrame or np.array
            Nested time series data frame.
        y : np.array
            Array of target values.
        """
        X = self._format_x_windows(x_windows)

        # during prediction, y=None, so only return X
        if y_windows is None:
            return X

        y = self._format_y_windows(y_windows)
        return X, y

    @staticmethod
    def _format_y_windows(y_windows):
        """Template method for formatting y windows"""
        raise NotImplementedError("abstract method")

    @staticmethod
    def _format_x_windows(x_windows):
        """Template method for formatting x windows"""
        raise NotImplementedError("abstract method")

    def _is_predictable(self, last_window):
        """Helper function to check if we can make predictions from last
        window"""
        return (
            len(last_window) == self.window_length_
            and np.sum(np.isnan(last_window)) == 0
            and np.sum(np.isinf(last_window)) == 0
        )


class ReducedTimeSeriesRegressorMixin:
    """Mixin class for reducing forecasting to time series regression"""

    @staticmethod
    def _format_x_windows(x_windows):
        """Helper function to combine windows from temporal cross-validation
        into nested
        pd.DataFrame used for solving forecasting via reduction to time
        series regression.

        Parameters
        ----------
        x_windows : list of pd.Series or np.array

        Returns
        -------
        X : pd.DataFrame
            Nested time series data frame.
        """
        # return nested dataframe
        return pd.DataFrame(pd.Series([pd.Series(xi) for xi in x_windows]))

    @staticmethod
    def _format_y_windows(y_windows):
        return np.array([np.asarray(yi) for yi in y_windows])


class ReducedTabularRegressorMixin:
    """Mixin class for reducing forecasting to tabular regression"""

    @staticmethod
    def _format_x_windows(x_windows):
        """Helper function to combine windows from temporal cross-validation
        into nested
        pd.DataFrame used for solving forecasting via reduction to time
        series regression.

        Parameters
        ----------
        x_windows : list of pd.Series or np.array

        Returns
        -------
        X : pd.DataFrame
            Nested time series data frame.
        """
        return np.vstack(x_windows)

    @staticmethod
    def _format_y_windows(y_windows):
        return np.vstack(y_windows)


class _DirectReducer(_RequiredForecastingHorizonMixin, BaseReducer):
    strategy = "direct"

    def fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """
        self._set_y_X(y, X)
        if X is not None:
            raise NotImplementedError("Exogenous variables `X` are not yet supported.")
        self._set_fh(fh)
        if len(self.fh.to_in_sample(self.cutoff)) > 0:
            raise NotImplementedError("In-sample predictions are not implemented")

        self.step_length_ = check_step_length(self.step_length)
        self.window_length_ = check_window_length(self.window_length)

        # for the direct reduction strategy, a separate forecaster is fitted
        # for each step ahead of the forecasting horizon
        self._cv = SlidingWindowSplitter(
            fh=self.fh.to_relative(self.cutoff),
            window_length=self.window_length_,
            step_length=self.step_length_,
            start_with_window=True,
        )

        # transform data using rolling window split
        X, Y_train = self._transform(y, X)

        # iterate over forecasting horizon
        self.regressors_ = []
        for i in range(len(self.fh)):
            y = Y_train[:, i]
            regressor = clone(self.regressor)
            regressor.fit(X, y)
            self.regressors_.append(regressor)

        self._is_fitted = True
        return self

    def _predict_last_window(
        self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA
    ):
        # use last window as new input data for time series regressors to
        # make forecasts
        # get last window from observation horizon
        last_window, _ = self._get_last_window()
        if not self._is_predictable(last_window):
            return self._predict_nan(fh)

        X_last = self._format_windows([last_window])

        # preallocate array for forecasted values
        y_pred = np.zeros(len(fh))

        # Iterate over estimators/forecast horizon
        for i, regressor in enumerate(self.regressors_):
            y_pred[i] = regressor.predict(X_last)
        return y_pred

    def _predict_in_sample(self, fh, X=None, return_pred_int=False, alpha=None):
        # it's not clear how the direct reducer would generate in-sample
        # predictions
        raise NotImplementedError("in-sample predictions are not implemented")


class _MultioutputReducer(_RequiredForecastingHorizonMixin, BaseReducer):
    strategy = "multioutput"

    def fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """
        self._set_y_X(y, X)
        if X is not None:
            raise NotImplementedError("Exogenous variables `X` are not yet supported.")
        self._set_fh(fh)
        if len(self.fh.to_in_sample(self.cutoff)) > 0:
            raise NotImplementedError("In-sample predictions are not implemented")

        self.step_length_ = check_step_length(self.step_length)
        self.window_length_ = check_window_length(self.window_length)

        # for the multioutput reduction strategy, a single forecaster is fitted
        # simultaneously to all the future steps in the forecasting horizon
        # by reducing to a forecaster that can handle multi-dimensional outputs
        self._cv = SlidingWindowSplitter(
            fh=self.fh.to_relative(self.cutoff),
            window_length=self.window_length_,
            step_length=self.step_length_,
            start_with_window=True,
        )

        # transform data using rolling window split
        X, Y_train = self._transform(y, X)

        # fit regressor to training data
        regressor = clone(self.regressor)
        regressor.fit(X, Y_train)
        self.regressor_ = regressor

        self._is_fitted = True
        return self

    def _predict_last_window(
        self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA
    ):
        # use last window as new input data for regressor to
        # make forecasts
        # get last window from observation horizon
        last_window, _ = self._get_last_window()
        if not self._is_predictable(last_window):
            return self._predict_nan(fh)

        X_last = self._format_windows([last_window])

        y_pred = self.regressor_.predict(X_last)

        # preallocate array for forecasted values
        # y_pred = np.zeros(len(fh))

        return y_pred[0]

    def _predict_in_sample(self, fh, X=None, return_pred_int=False, alpha=None):
        raise NotImplementedError("in-sample predictions are not implemented")


class _RecursiveReducer(_OptionalForecastingHorizonMixin, BaseReducer):
    strategy = "recursive"

    def fit(self, y, X=None, fh=None):
        """Fit to training data.

        Parameters
        ----------
        y : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """
        # input checks
        if X is not None:
            raise NotImplementedError("Exogenous variables `X` are not yet supported.")

        # set values
        self._set_y_X(y, X)
        self._set_fh(fh)

        self.step_length_ = check_step_length(self.step_length)
        self.window_length_ = check_window_length(self.window_length)

        # set up cv iterator, for recursive strategy, a single estimator
        # is fit for a one-step-ahead forecasting horizon and then called
        # iteratively to predict multiple steps ahead
        self._cv = SlidingWindowSplitter(
            fh=1,
            window_length=self.window_length_,
            step_length=self.step_length_,
            start_with_window=True,
        )

        # transform data into tabular form
        X_train_tab, y_train_tab = self._transform(y, X)

        # fit base regressor
        regressor = clone(self.regressor)
        regressor.fit(X_train_tab, y_train_tab.ravel())
        self.regressor_ = regressor

        self._is_fitted = True
        return self

    def _predict_last_window(
        self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA
    ):
        """Predict"""
        # compute prediction
        # prepare recursive predictions
        fh_max = fh.to_relative(self.cutoff)[-1]
        y_pred = np.zeros(fh_max)

        # get last window from observation horizon
        last_window, _ = self._get_last_window()
        if not self._is_predictable(last_window):
            return self._predict_nan(fh)

        # recursively predict iterating over forecasting horizon
        for i in range(fh_max):
            X_last = self._format_windows(
                [last_window]
            )  # convert data into required input format
            y_pred[i] = self.regressor_.predict(
                X_last
            )  # make forecast using fitted regressor

            # update last window with previous prediction
            last_window = np.append(last_window, y_pred[i])[-self.window_length_ :]

        fh_idx = fh.to_indexer(self.cutoff)
        return y_pred[fh_idx]


##############################################################################
# reduction to regression
class DirectTabularRegressionForecaster(ReducedTabularRegressorMixin, _DirectReducer):
    """
    Forecasting based on reduction to tabular regression with a direct
    reduction strategy.
    For the direct reduction strategy, a separate forecaster is fitted
    for each step ahead of the forecasting horizon

    Parameters
    ----------
    regressor : sklearn estimator object
        Define the regression model type.
    window_length : int, optional (default=10)
        The length of the sliding window used to transform the series into
        a tabular matrix
    step_length : int, optional (default=1)
        The number of time steps taken at each step of the sliding window
        used to transform the series into a tabular matrix.
    """

    pass


class MultioutputTabularRegressionForecaster(
    ReducedTabularRegressorMixin, _MultioutputReducer
):
    """
    Forecasting based on reduction to tabular regression with a multioutput
    reduction strategy.
    For the multioutput reduction strategy, a single forecaster is fitted
    simultaneously to all the future steps in the forecasting horizon

    Parameters
    ----------
    regressor : sklearn estimator object
        Define the regression model type.
    window_length : int, optional (default=10)
        The length of the sliding window used to transform the series into
        a tabular matrix
    step_length : int, optional (default=1)
        The number of time steps taken at each step of the sliding window
        used to transform the series into a tabular matrix.
    """

    pass


class RecursiveTabularRegressionForecaster(
    ReducedTabularRegressorMixin, _RecursiveReducer
):
    """
    Forecasting based on reduction to tabular regression with a recursive
    reduction strategy.
    For the recursive reduction strategy, a single estimator is
    fit for a one-step-ahead forecasting horizon and then called
    iteratively to predict multiple steps ahead.

    Parameters
    ----------
    regressor : sklearn estimator object
        Define the regression model type.
    window_length : int, optional (default=10)
        The length of the sliding window used to transform the series into
        a tabular matrix
    step_length : int, optional (default=1)
        The number of time steps taken at each step of the sliding window
        used to transform the series into a tabular matrix.
    """

    pass


##############################################################################
# reduction to time series regression
class DirectTimeSeriesRegressionForecaster(
    ReducedTimeSeriesRegressorMixin, _DirectReducer
):
    """
    Forecasting based on reduction to time series regression with a direct
    reduction strategy.
    For the direct reduction strategy, a separate forecaster is fitted
    for each step ahead of the forecasting horizon

    Parameters
    ----------
    regressor : sktime estimator object
        Define the type of time series regression model.
    window_length : int, optional (default=10)
        The length of the sliding window used to transform the series into
        a tabular matrix
    step_length : int, optional (default=1)
        The number of time steps taken at each step of the sliding window
        used to transform the series into a tabular matrix.
    """

    pass


class RecursiveTimeSeriesRegressionForecaster(
    ReducedTimeSeriesRegressorMixin, _RecursiveReducer
):
    """
    Forecasting based on reduction to time series regression with a recursive
    reduction strategy.
    For the recursive reduction strategy, a single estimator is
    fit for a one-step-ahead forecasting horizon and then called
    iteratively to predict multiple steps ahead.

    Parameters
    ----------
    regressor : sktime estimator object
        Define the type of time series regression model.
    window_length : int, optional (default=10)
        The length of the sliding window used to transform the series into
        a tabular matrix
    step_length : int, optional (default=1)
        The number of time steps taken at each step of the sliding window
        used to transform the series into a tabular matrix.
    """

    pass


##############################################################################
# factory methods for easier user interface, but not tunable as it's not an
# estimator


@deprecated("Please use `make_reduction` from `sktime.forecasting.compose` instead.")
def ReducedForecaster(
    estimator, scitype, strategy="recursive", window_length=10, step_length=1
):
    """
    Forecasting based on reduction

    When fitting, a rolling window approach is used to first transform the
    target series into panel data which is
    then used to train a estimator. During prediction, the last
    available data is used as input to the
    fitted estimators to make forecasts.

    Parameters
    ----------
    estimator : a estimator of type given by parameter scitype
    scitype : str
        Can be 'regressor' or 'ts-regressor'
    strategy : str {"direct", "recursive", "multioutput"}, optional
        Strategy to generate predictions
    window_length : int, optional (default=10)
    step_length : int, optional (default=1)

    References
    ----------
    ..[1] Bontempi, Gianluca & Ben Taieb, Souhaib & Le Borgne, Yann-Aël. (
    2013).
      Machine Learning Strategies for Time Series Forecasting.
    """
    if step_length != 1:
        raise ValueError("`step_length` is no longer supported.")
    return make_reduction(
        estimator, strategy=strategy, window_length=window_length, scitype=scitype
    )


def make_reduction(
    estimator,
    strategy="recursive",
    window_length=10,
    scitype="infer",
):
    """
    Create a reduction forecaster based on a tabular or time series
    regression estimator.

    When fitting, a sliding window approach is used to first transform the
    target series into tabular or panel data, which is then used to train a
    estimator. During prediction, the last available data is used as input to the
    fitted estimators to generate forecasts.

    Parameters
    ----------
    estimator : an estimator instance
        Either a tabular regressor from scikit-learn or a time series regressor from
        sktime.
    strategy : str, optional (default="recursive")
        Must be one of "direct", "recursive", "multioutput". The strategy to apply
        estimator to forecasting task.
    window_length : int, optional (default=10)
        Window length used in sliding window transformation.
    scitype : str, optional (default="inferred")
        Must be one of "inferred", "tabular-regressor" or "time-series-regressor". If
        the scitype cannot be inferred, please specify it explicitly.

    Returns
    -------
    estimator : an Estimator instance
        A reduction forecaster

    References
    ----------
    ..[1] Bontempi, Gianluca & Ben Taieb, Souhaib & Le Borgne, Yann-Aël. (2013).
      Machine Learning Strategies for Time Series Forecasting.
    """
    # We provide this function as a factory method for easier usage.
    strategy = _check_strategy(strategy)
    scitype = _check_scitype(scitype)

    if scitype == "infer":
        scitype = _infer_scitype(estimator)

    Forecaster = _get_forecaster(scitype, strategy)
    return Forecaster(regressor=estimator, window_length=window_length)


def _check_strategy(strategy):
    valid_strategies = ("direct", "recursive", "multioutput")
    if strategy not in valid_strategies:
        raise ValueError(f"Unknown `strategy`, please use one of {valid_strategies}.")
    return strategy


def _check_scitype(scitype):
    valid_scitypes = ("infer", "tabular-regressor", "time-series-regressor")
    if scitype not in valid_scitypes:
        raise ValueError(f"Unknown `scitype`, please use one of {valid_scitypes}.")

    return scitype


def _infer_scitype(estimator):
    # We can check if estimator is an instance of scikit-learn's RegressorMixin or
    # of sktime's BaseRegressor, otherwise we raise an error.

    if isinstance(estimator, RegressorMixin):
        return "tabular-regressor"
    elif isinstance(estimator, BaseRegressor):
        return "time-series-regressor"
    else:
        raise ValueError(
            "The `scitype` of the given `estimator` cannot be inferred. "
            "Please specify the `scitype` explicitly."
        )


def _get_forecaster(scitype, strategy):
    """Helper function to select forecaster for a given scientific type (
    scitype)
    and reduction strategy"""

    registry = {
        "tabular-regressor": {
            "direct": DirectTabularRegressionForecaster,
            "recursive": RecursiveTabularRegressionForecaster,
            "multioutput": MultioutputTabularRegressionForecaster,
        },
        "time-series-regressor": {
            "direct": DirectTimeSeriesRegressionForecaster,
            "recursive": RecursiveTimeSeriesRegressionForecaster,
            # "multioutput": MultioutputTimeSeriesRegressionForecaster,
        },
    }
    return registry.get(scitype).get(strategy)

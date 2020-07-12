#!/usr/bin/env python3 -u
# coding: utf-8
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

__all__ = ["NaiveForecaster"]
__author__ = "Markus Löning"

from warnings import warn

import numpy as np
from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.base._sktime import BaseLastWindowForecaster
from sktime.forecasting.base._sktime import OptionalForecastingHorizonMixin
from sktime.utils.validation.forecasting import check_sp
from sktime.utils.validation.forecasting import check_window_length


class NaiveForecaster(OptionalForecastingHorizonMixin,
                      BaseLastWindowForecaster):
    """
    NaiveForecaster is a forecaster that makes forecasts using simple
    strategies.

    Parameters
    ----------
    strategy : str{"last", "mean", "drift"}, optional (default="last")
        Strategy used to make forecasts:

        * "last" : forecast the last value in the
                    training series when sp is 1
        * "mean" : forecast the mean of (a given window)
                                of the training series
        When sp is not 1, computes the "last" and "mean"
        strategies based on values of the same season
        * "drift": forecast the values increasing or
                                decreasing along a linear relationship
                                 from last window

    sp : int or None, optional (default=None)
        Seasonal periodicity to use in the seasonal forecast strategies.
         If None, naive strategy will be used

    window_length : int or None, optional (default=None)
        Window length to use in the `mean` strategy. If None, entire training
            series will be used.
    """

    def __init__(self, strategy="last", window_length=None, sp=1):
        super(NaiveForecaster, self).__init__()
        # input checks
        # allowed strategies to include: last, constant, seasonal-last,
        # mean, median
        allowed_strategies = ("last", "mean", "drift")
        if strategy not in allowed_strategies:
            raise ValueError(
                f"Unknown strategy: {strategy}; expected one of "
                f"{allowed_strategies}")
        self.strategy = strategy
        self.sp = sp
        self.window_length = window_length

        self.sp_ = None

    def fit(self, y_train, fh=None, X_train=None):
        """Fit to training data.

        Parameters
        ----------
        y_train : pd.Series
            Target time series to which to fit the forecaster.
        fh : int, list or np.array, optional (default=None)
            The forecasters horizon with the steps ahead to to predict.
        X_train : pd.DataFrame, optional (default=None)
            Exogenous variables are ignored
        Returns
        -------
        self : returns an instance of self.
        """  # X_train is ignored
        self._set_oh(y_train)
        self._set_fh(fh)

        if self.strategy == "last":
            if self.window_length is not None:
                warn("For the `last` strategy, "
                     "the `window_length` value will be ignored.")

        if self.strategy == "drift":
            if self.sp != 1:
                warn("For the `drift` strategy, "
                     "the `sp` value will be ignored.")

        if self.strategy == "last" and self.sp == 1:
            self.window_length_ = 1

        if self.strategy == "last" and self.sp != 1:
            self.sp_ = check_sp(self.sp)

            # window length we need for forecasts is just the
            # length of seasonal periodicity
            self.window_length_ = self.sp_

        if self.strategy == "mean":
            # check window length is greater than sp for seasonal mean
            if self.window_length is not None and self.sp != 1:
                if self.window_length < self.sp:
                    raise ValueError(f"The "
                                     f"`window_length`: {self.window_length}"
                                     f" is lesser than the"
                                     f" `sp`: {self.sp}.")
            self.window_length_ = check_window_length(self.window_length)
            self.sp_ = check_sp(self.sp)

        if self.strategy == "drift":
            self.window_length_ = check_window_length(self.window_length)

        #  if not given, set default window length for the mean strategy
        if self.strategy in ("mean", "drift") and self.window_length is None:
            self.window_length_ = len(y_train)

        # check window length
        if self.window_length_ > len(self.oh):
            param = "sp" if self.strategy == "last" and self.sp != 1 \
                else "window_length_"
            raise ValueError(
                f"The {param}: {self.window_length_} is larger than "
                f"the training series.")

        self._is_fitted = True
        return self

    def _predict_last_window(self, fh, X=None, return_pred_int=False,
                             alpha=DEFAULT_ALPHA):
        """Internal predict"""
        last_window = self._get_last_window()

        # if last window only contains missing values, return nan
        if np.all(np.isnan(last_window)) or len(last_window) == 0:
            return self._predict_nan(fh)

        elif self.strategy == "last" and self.sp == 1:
            return np.repeat(last_window[-1], len(fh))

        elif self.strategy == "last" and self.sp != 1:
            # we need to replicate the last window if max(fh) is larger than
            # sp,
            # so that we still make forecasts by repeating the last value
            # for that season,
            # assume fh is sorted, i.e. max(fh) == fh[-1]
            if fh[-1] > self.sp_:
                reps = np.int(np.ceil(fh[-1] / self.sp_))
                last_window = np.tile(last_window, reps=reps)

            # get zero-based index by subtracting the minimum
            fh_idx = fh.index_like(self.cutoff)
            return last_window[fh_idx]

        elif self.strategy == "mean" and self.sp == 1:
            return np.repeat(np.nanmean(last_window), len(fh))

        elif self.strategy == "mean" and self.sp != 1:
            last_window = last_window.astype(float)
            last_window = np.pad(last_window,
                                 (0, self.sp_ - len(last_window) % self.sp_),
                                 'constant',
                                 constant_values=(-1))

            last_window = last_window.reshape(np.int(np.
                                                     ceil(len(last_window) /
                                                          self.sp_)),
                                              self.sp_)

            indices = np.where(last_window == -1)[-1]
            last_window[-1][indices] =\
                (last_window.sum(axis=0)[indices] +
                 1) / (last_window.shape[-1] - 1)

            last_window = last_window.mean(axis=0)

            # we need to replicate the last window if max(fh) is
            # larger than sp,
            # so that we still make forecasts by repeating the
            # last value for that season,
            # assume fh is sorted, i.e. max(fh) == fh[-1]
            # only slicing all the last seasons into last_window
            if fh[-1] > self.sp_:
                reps = np.int(np.ceil(fh[-1] / self.sp_))
                last_window =\
                    np.tile(last_window,
                            reps=reps)

            # get zero-based index by subtracting the minimum
            fh_idx = fh.index_like(self.cutoff)
            return last_window[fh_idx]

        elif self.strategy == "drift":
            if any(last_window) is not np.nan:
                drift = np.mean(np.diff(last_window))

                # get zero-based index by subtracting the minimum
                fh_idx = fh.index_like(self.cutoff)

                last_window =np.arange(last_window[-1],
                                       last_window[-1]+\
                                       drift*(max(fh_idx)+1),
                                       drift)
                return last_window[fh_idx]

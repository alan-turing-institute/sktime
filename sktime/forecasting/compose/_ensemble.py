#!/usr/bin/env python3 -u
# coding: utf-8
<<<<<<< HEAD
=======
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed

__author__ = ["Markus Löning"]
__all__ = ["EnsembleForecaster"]

import pandas as pd
<<<<<<< HEAD
from sktime.forecasting.base._meta import BaseHeterogenousEnsembleForecaster
from sktime.forecasting.base._sktime import OptionalForecastingHorizonMixin
from sktime.forecasting.base._base import DEFAULT_ALPHA


class EnsembleForecaster(OptionalForecastingHorizonMixin, BaseHeterogenousEnsembleForecaster):
=======
from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.base._meta import BaseHeterogenousEnsembleForecaster
from sktime.forecasting.base._sktime import OptionalForecastingHorizonMixin


class EnsembleForecaster(OptionalForecastingHorizonMixin,
                         BaseHeterogenousEnsembleForecaster):
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
    """Ensemble of forecasters

    Parameters
    ----------
    forecasters : list of (str, estimator) tuples
    n_jobs : int or None, optional (default=None)
<<<<<<< HEAD
        The number of jobs to run in parallel for fit. None means 1 unless in a joblib.parallel_backend context.
=======
        The number of jobs to run in parallel for fit. None means 1 unless
        in a joblib.parallel_backend context.
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed
        -1 means using all processors.
    """

    _required_parameters = ["forecasters"]

    def __init__(self, forecasters, n_jobs=None):
        self.n_jobs = n_jobs
        super(EnsembleForecaster, self).__init__(forecasters=forecasters)

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
        """
        self._set_oh(y_train)
        self._set_fh(fh)
        names, forecasters = self._check_forecasters()
        self._fit_forecasters(forecasters, y_train, fh=fh, X_train=X_train)
        self._is_fitted = True
        return self

    def update(self, y_new, X_new=None, update_params=False):
        """Update fitted paramters

        Parameters
        ----------
        y_new : pd.Series
        X_new : pd.DataFrame
        update_params : bool, optional (default=False)

        Returns
        -------
        self : an instance of self
        """
        self.check_is_fitted()
        self._set_oh(y_new)
        for forecaster in self.forecasters_:
            forecaster.update(y_new, X_new=X_new, update_params=update_params)
        return self

<<<<<<< HEAD
    def transform(self, fh=None, X=None):
        self.check_is_fitted()
        self._set_fh(fh)
        return pd.concat(self._predict_forecasters(fh=fh, X=X), axis=1)

    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        if return_pred_int:
            raise NotImplementedError()
        return pd.concat(self._predict_forecasters(fh=fh, X=X), axis=1).mean(axis=1)
=======
    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        if return_pred_int:
            raise NotImplementedError()
        return pd.concat(self._predict_forecasters(fh=fh, X=X), axis=1).mean(
            axis=1)
>>>>>>> 67c56be8b1e838f2628df829946f795b7dba9aed

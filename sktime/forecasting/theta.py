# -*- coding: utf-8 -*-
__all__ = ["ThetaForecaster", "AutoThetaForcaster"]
__author__ = ["@big-o", "Markus Löning", "Aditya"]

from warnings import warn

import numpy as np
import pandas as pd
from scipy.stats import norm, linregress

from sktime.forecasting.base._base import DEFAULT_ALPHA
from sktime.forecasting.exp_smoothing import ExponentialSmoothing
from sktime.transformations.series.detrend import Deseasonalizer
from statsmodels.tsa.stattools import acf
from statsmodels.tsa.seasonal import seasonal_decompose
from sktime.utils.slope_and_trend import _fit_trend
from sktime.utils.validation.forecasting import check_sp
from sktime.utils.validation.forecasting import check_y_X


class AutoThetaForcaster:
    """
    This is a test description.
    inpt : pandas DataFrame
    ppy : int
    """

    def SeasonalityTest(self, inpt, ppy):
        tcrit = 1.645
        if len(inpt) < 3 * ppy:
            test_seasonal = False

        else:
            xcaf = acf(inpt)[acf[-1, 1, 1]]
            clim = tcrit / np.sqrt(len(inpt)) * np.sqrt(np.cumsum([1, 2 * xcaf ** 2]))
            test_seasonal = abs(xcaf[ppy]) > clim[ppy]

            if test_seasonal is None:
                test_seasonal = False

        return test_seasonal

    def Theta_models_fit(
        self, inpt, fh, theta, curve, model, seasonality, plot=False, positive=True
    ):
        """
        inpt : Pandas dataframe
        fh : int
        theta : float
        seasonality : "N", "A", or anything else
        """

        # Check if the inputs are valid
        if theta < 1:
            theta = 1
        if fh < 1:
            fh = 1

        # Estimate theta line weights
        # Implementation of simple naive forcaster

        ##### This part needs to be replaced        ######
        outtest = np.array([inpt[-1] for i in range(fh)])
        #####                                       ######

        wses = 1 / theta
        wlrl = 1 - wses

        # Estimate seasonaly adjusted time series
        ppy = len(inpt.columns)

        if seasonality == "N":
            des_inpt = inpt
            SIout = np.ones(fh)
            SIin = np.ones(len(inpt))
        elif seasonality == "A":
            Dec = seasonal_decompose(inpt, model="additive")
            des_inpt = inpt - Dec.seasonal
            SIin = Dec.seasonal
            Dec_values = Dec.seasonal[(len(Dec.seasonal) - ppy + 1) : len(Dec.seasonal)]
            SIout = pd.Series(
                np.tile(Dec_values, fh), index=list(Dec_values.index) * fh
            ).head(n=fh)
        else:
            Dec = seasonal_decompose(inpt, model="multiplicative")
            des_inpt = inpt / Dec.seasonal
            SIin = Dec.seasonal
            Dec_values = Dec.seasonal[(len(Dec.seasonal) - ppy + 1) : len(Dec.seasonal)]
            SIout = pd.Series(
                np.tile(Dec_values, fh), index=list(Dec_values.index) * fh
            ).head(n=fh)

        # Estimate theta line zero
        observations = len(des_inpt.values.reshape(-1, 1))
        xs = list(range(1, observations + 1))
        xf = xff = list(range((observations + 1), (observations + fh + 1)))

        # Add all the values of Des_inpt to a list
        des_inpt_lst = []
        for indx in range(len(des_inpt)):
            des_inpt_lst.extend(des_inpt.iloc[indx].values)

        dta = pd.DataFrame(data={"des_inpt": des_inpt_lst, "xs": xs})
        newdf = pd.Series(data={"xs": xff})

        if curve == "Exp":
            estimate = linregress(xs, np.log(des_inpt))
            thetalineIn = np.exp(
                [elmnt * estimate.slope + estimate.intercept for elmnt in xs]
            ).reshape(inpt.shape)
            # Reshape thetalineIn in the dataframe like inpt
            thetaline0In = pd.DataFrame(
                data=thetalineIn, index=list(inpt.index), columns=list(inpt.columns)
            )
            thetaline0Out = (
                np.exp(
                    [
                        elmnt * estimate.slope + estimate.intercept
                        for elmnt in newdf.values[0]
                    ]
                )
                + outtest
                - outtest
            )


class ThetaForecaster(ExponentialSmoothing):
    """
    Theta method of forecasting.

    The theta method as defined in [1]_ is equivalent to simple exponential
    smoothing
    (SES) with drift. This is demonstrated in [2]_.

    The series is tested for seasonality using the test outlined in A&N. If
    deemed
    seasonal, the series is seasonally adjusted using a classical
    multiplicative
    decomposition before applying the theta method. The resulting forecasts
    are then
    reseasonalised.

    In cases where SES results in a constant forecast, the theta forecaster
    will revert
    to predicting the SES constant plus a linear trend derived from the
    training data.

    Prediction intervals are computed using the underlying state space model.

    Parameters
    ----------

    initial_level : float, optional
        The alpha value of the simple exponential smoothing, if the value is
        set then
        this will be used, otherwise it will be estimated from the data.

    deseasonalize : bool, optional (default=True)
        If True, data is seasonally adjusted.

    sp : int, optional (default=1)
        The number of observations that constitute a seasonal period for a
        multiplicative deseasonaliser, which is used if seasonality is
        detected in the
        training data. Ignored if a deseasonaliser transformer is provided.
        Default is
        1 (no seasonality).

    Attributes
    ----------

    initial_level_ : float
        The estimated alpha value of the SES fit.

    drift_ : float
        The estimated drift of the fitted model.

    se_ : float
        The standard error of the predictions. Used to calculate prediction
        intervals.

    References
    ----------

    .. [1] `Assimakopoulos, V. and Nikolopoulos, K. The theta model: a
    decomposition
           approach to forecasting. International Journal of Forecasting 16,
           521-530,
           2000.
           <https://www.sciencedirect.com/science/article/pii
           /S0169207000000662>`_

    .. [2] `Hyndman, Rob J., and Billah, Baki. Unmasking the Theta method.
           International J. Forecasting, 19, 287-290, 2003.
           <https://www.sciencedirect.com/science/article/pii
           /S0169207001001431>`_
    """

    _fitted_param_names = ("initial_level", "smoothing_level")

    def __init__(self, initial_level=None, deseasonalize=True, sp=1):

        self.sp = sp
        self.deseasonalize = deseasonalize

        self.deseasonalizer_ = None
        self.trend_ = None
        self.initial_level_ = None
        self.drift_ = None
        self.se_ = None
        super(ThetaForecaster, self).__init__(initial_level=initial_level, sp=sp)

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
        y, _ = check_y_X(y, X)
        sp = check_sp(self.sp)
        if sp > 1 and not self.deseasonalize:
            warn("`sp` is ignored when `deseasonalise`=False")

        if self.deseasonalize:
            self.deseasonalizer_ = Deseasonalizer(sp=self.sp, model="multiplicative")
            y = self.deseasonalizer_.fit_transform(y)

        # fit exponential smoothing forecaster
        # find theta lines: Theta lines are just SES + drift
        super(ThetaForecaster, self).fit(y, fh=fh)
        self.initial_level_ = self._fitted_forecaster.params["smoothing_level"]

        # compute trend
        self.trend_ = self._compute_trend(y)
        self._is_fitted = True
        return self

    def _predict(self, fh, X=None, return_pred_int=False, alpha=DEFAULT_ALPHA):
        """
        Make forecasts.

        Parameters
        ----------

        fh : array-like
            The forecasters horizon with the steps ahead to to predict.
            Default is
            one-step ahead forecast, i.e. np.array([1]).

        Returns
        -------

        y_pred : pandas.Series
            Returns series of predicted values.
        """
        y_pred = super(ThetaForecaster, self)._predict(
            fh, X, return_pred_int=False, alpha=alpha
        )

        # Add drift.
        drift = self._compute_drift()
        y_pred += drift

        if self.deseasonalize:
            y_pred = self.deseasonalizer_.inverse_transform(y_pred)

        if return_pred_int:
            pred_int = self.compute_pred_int(y_pred=y_pred, alpha=alpha)
            return y_pred, pred_int

        return y_pred

    @staticmethod
    def _compute_trend(y):
        # Trend calculated through least squares regression.
        coefs = _fit_trend(y.values.reshape(1, -1), order=1)
        return coefs[0, 0] / 2

    def _compute_drift(self):
        fh = self.fh.to_relative(self.cutoff)
        if np.isclose(self.initial_level_, 0.0):
            # SES was constant, so revert to simple trend
            drift = self.trend_ * fh
        else:
            # Calculate drift from SES parameters
            n_timepoints = len(self._y)
            drift = self.trend_ * (
                fh
                + (1 - (1 - self.initial_level_) ** n_timepoints) / self.initial_level_
            )

        return drift

    def _compute_pred_err(self, alphas):
        """
        Get the prediction errors for the forecast.
        """
        self.check_is_fitted()

        n_timepoints = len(self._y)

        self.sigma_ = np.sqrt(self._fitted_forecaster.sse / (n_timepoints - 1))
        sem = self.sigma_ * np.sqrt(
            self.fh.to_relative(self.cutoff) * self.initial_level_ ** 2 + 1
        )

        errors = []
        for alpha in alphas:
            z = _zscore(1 - alpha)
            error = z * sem
            errors.append(pd.Series(error, index=self.fh.to_absolute(self.cutoff)))

        return errors

    def update(self, y, X=None, update_params=True):
        super(ThetaForecaster, self).update(
            y, X, update_params=False
        )  # use custom update_params routine
        if update_params:
            if self.deseasonalize:
                y = self.deseasonalizer_.transform(self._y)  # use updated y
            self.initial_level_ = self._fitted_forecaster.params["smoothing_level"]
            self.trend_ = self._compute_trend(y)
        return self


def _zscore(level: float, two_tailed: bool = True) -> float:
    """
    Calculate a z-score from a confidence level.

    Parameters
    ----------

    level : float
        A confidence level, in the open interval (0, 1).

    two_tailed : bool (default=True)
        If True, return the two-tailed z score.

    Returns
    -------

    z : float
        The z score.
    """
    alpha = 1 - level
    if two_tailed:
        alpha /= 2

    return -norm.ppf(alpha)

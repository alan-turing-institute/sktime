#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus Löning"]
__all__ = ["BaseEstimator"]

from sklearn.base import BaseEstimator as _BaseEstimator
from sktime.exceptions import NotFittedError


class BaseEstimator(_BaseEstimator):

    def __init__(self):
        self._is_fitted = False

    @property
    def is_fitted(self):
        """Has `fit` been called?"""
        return self._is_fitted

    def check_is_fitted(self):
        """Check if the forecaster has been fitted.

        Raises
        ------
        NotFittedError
            if the forecaster has not been fitted yet.
        """
        if not self.is_fitted:
            raise NotFittedError(f"This instance of {self.__class__.__name__} has not "
                                 f"been fitted yet; please call `fit` first.")

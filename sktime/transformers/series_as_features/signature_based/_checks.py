# -*- coding: utf-8 -*-
"""
_checks.py
====================
Contains a reusable decorator function to handle the sklearn signature checks.
"""
import functools
import numpy as np
import pandas as pd
from sktime.utils.validation.series_as_features import check_X, check_X_y
from sktime.utils.data_container import from_nested_to_3d_numpy


def handle_sktime_signatures(check_fitted=False, return_numpy=True):
    """Simple function for handling the sktime checks in signature modules.

    This decorator assumes that the input arguments to the function are either
    of the form:
        (self, data, labels)
    or
        (self, data).

    If this is in sktime format data, it will check the data and labels are of
    the correct form, and then
    """

    def real_decorator(func):
        """Reusable decorator to handle the sktime checks and convert the data
        to a torch Tensor.
        """

        @functools.wraps(func)
        def wrapper(self, data, labels=None, **kwargs):
            # Check if pandas so we can convert back
            is_pandas = True if isinstance(data, pd.DataFrame) else False
            pd_idx = data.index if is_pandas else None

            # Fit checks
            if check_fitted:
                self.check_is_fitted()

            # First convert to pandas so everything is the same format
            if labels is None:
                data = check_X(data, enforce_univariate=False, coerce_to_pandas=True)
            else:
                data, labels = check_X_y(
                    data, labels, enforce_univariate=False, coerce_to_pandas=True
                )

            # Now convert it to a numpy array
            # Note sktime uses [N, C, L] whereas signature code uses shape
            # [N, L, C] (C being channels) so we must transpose.
            if not isinstance(data, np.ndarray):
                data = from_nested_to_3d_numpy(data)
            data = np.transpose(data, [0, 2, 1])

            # Apply the function to the transposed array
            if labels is None:
                output = func(self, data, **kwargs)
            else:
                output = func(self, data, labels, **kwargs)

            # Convert back
            if all([is_pandas, isinstance(output, np.ndarray), not return_numpy]):
                output = pd.DataFrame(index=pd_idx, data=output)

            return output

        return wrapper

    return real_decorator

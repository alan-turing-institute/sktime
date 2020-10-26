#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)

# sktime supports a number of soft dependencies which are necessary for using
# a certain module but otherwise not necessary. Here we check if soft
# dependencies have been properly isolated and are not required to run other
# modules.
import pkgutil
import re
from importlib import import_module

SOFT_DEPENDENCIES = {
    "sktime.benchmarking.evaluation": ["matplotlib"],
    "sktime.transformers.series_as_features.tsfresh": ["tsfresh"],
    "sktime.forecasting.arima": ["pmdarima"],
    "sktime.forecasting.all": ["pmdarima"],
    "sktime.classification.all": ["tsfresh"],
    "sktime.regression.all": ["tsfresh"],
}
MODULES_TO_IGNORE = ("tests", "contrib")


def _extract_dependency_from_error_msg(msg):
    # We raise an user-friendly error if a soft dependency is missing in the
    # `check_soft_dependencies` function. In the error message, the missing
    # dependency is printed in single quotation marks, so we can use that here to
    # extract and return the dependency name.
    match = re.search(r"\'(.+?)\'", msg)
    if match:
        return match.group(1)
    else:
        raise ValueError("No dependency found in error msg.")


for _, module, _ in pkgutil.walk_packages(path=["./sktime/"], prefix="sktime."):

    # Split the full module into its parts and skip if desired
    mod_parts = module.split(".")
    if any(part in MODULES_TO_IGNORE for part in mod_parts):
        continue

    # We try importing all modules and catch exceptions due to missing dependencies
    try:
        import_module(module)
    except ModuleNotFoundError as e:
        error_msg = str(e)

        # Check if appropriate exception with useful error message is raised as
        # defined in the `_check_soft_dependencies` function
        expected_error_msg = (
            "is a soft dependency and not included in the sktime " "installation"
        )
        if expected_error_msg not in error_msg:
            raise RuntimeError(
                f"The module: {module} seems to require a soft "
                f"dependency, but does not raise an appropriate error "
                f"message when the soft dependency is missing. Please "
                f"use our `_check_soft_dependencies` function to "
                f"raise a more appropriate error message."
            ) from e

        # If the error is raised in a module which does depend on a soft dependency,
        # we ignore and skip it
        dependencies = SOFT_DEPENDENCIES.get(module, [])
        if any(dependency in error_msg for dependency in dependencies):
            continue

        # Otherwise we raise an error
        dependency = _extract_dependency_from_error_msg(error_msg)
        raise ModuleNotFoundError(
            f"The module: {module} should not require any soft dependencies, "
            f"but tried importing: '{dependency}'."
        ) from e

# -*- coding: utf-8 -*-
from sktime.base import BaseEstimator


from sktime.transformations.base import BaseTransformer


class OnlineUnsupervisedPipeline(BaseEstimator):
    """
    Parameters
    ----------
    steps : array of lists
        list comprised of three elements:
            1. name of step (string),
            2. algorithm (object),
            3. input (dictionary) key value paris for fit() method of algorithm
    interface: sting
        `simple`(default) or `advanced`.
            If `simple` `fit` method of the object is called.
            If `advanced` name of method can be specified like this:
            (`name of step`, `algorithm`, `input`), where input:
        input_dict = [
            {
                function: name of function to be called (fit, transform, predict ...),
                arguments: key value pairs(value is name of step) ,
            },
            {
                function: name of function to be called,
                arguments: key value pairs(value is name of step),
            },
            ......
        ]

    """

    def __init__(self, steps, interface="simple"):
        self._steps = steps

    def _iter(self):
        for name, alg, arguments in self._steps:
            yield name, alg, arguments

    def _check_steps_for_values(self, value):
        for step in self._steps:
            if value in step:
                return step[1].step_result
        return None

    def _process_arguments(self, arguments):
        """
        Checks arguments for consistency.

        Replace key word 'original' with X

        Replace string step name with step fit return result

        Parameters
        ----------
        arguments : dictionary
            key-value for fit() method of algorithm
        """

        returned_arguments_kwarg = arguments.copy()
        if arguments is None:
            return arguments
        for key, value in returned_arguments_kwarg.items():
            if value == "original":
                returned_arguments_kwarg[key] = self._X
                continue
            if type(value) == list:
                out = []
                for list_val in value:
                    returned_step_value = self._check_steps_for_values(list_val)
                    if returned_step_value is not None:
                        out.append(returned_step_value)
                returned_arguments_kwarg[key] = out
                continue
            # go through all steps and look for returned values
            returned_step_value = self._check_steps_for_values(value)
            if returned_step_value is not None:
                returned_arguments_kwarg[key] = returned_step_value

        return returned_arguments_kwarg

    def fit(self, X):
        self._X = X
        for _, alg, arguments in self._iter():

            arguments = self._process_arguments(arguments)
            # Transformers are instances of BaseTransformer and BaseEstimator
            # Estimators are only instances of BaseEstimator
            if isinstance(alg, BaseTransformer) and isinstance(alg, BaseEstimator):
                alg.fit_transform(**arguments)
            if not isinstance(alg, BaseTransformer) and isinstance(alg, BaseEstimator):
                alg.fit(**arguments)

        return self

    def predict(self, X):

        self._X = X

        for _, alg, arguments in self._iter():
            arguments = self._process_arguments(arguments)
            if isinstance(alg, BaseTransformer) and isinstance(alg, BaseEstimator):
                return alg.transform(**arguments)
            if not isinstance(alg, BaseTransformer) and isinstance(alg, BaseEstimator):
                return alg.predict(**arguments)

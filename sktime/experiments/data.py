import os
from sktime.utils.load_data import load_from_tsfile_to_dataframe
from sktime.utils.results_writing import write_results_to_uea_format
from sktime.highlevel import TSCTask, ForecastingTask
import re
import pandas as pd
from abc import ABC, abstractmethod
import numpy as np
import csv

class DatasetHDD:
    """
    Another class for holding the data
    """
    def __init__(self, dataset_loc, dataset_name, train_test_exists=True, sufix_train='_TRAIN.ts', suffix_test='_TEST.ts' ,target='target'):
        """
        Parameters
        ----------
        dataset_loc: string
            path on disk where the dataset is saved. Path to directory without the file name should be provided
        dataset_name: string
            Name of the dataset
        train_test_exists: Boolean
            flag whether the test train split already exists
        sufix_train: string
            train file suffix
        suffix_test: string
            test file suffix

        Returns
        -------
        pandas DataFrame:
            dataset in pandas DataFrame format
        """
        self._dataset_loc = dataset_loc
        self._dataset_name = dataset_name
        self._train_test_exists = train_test_exists
        self._target = target
        self._suffix_train = sufix_train
        self._suffix_test = suffix_test

    @property
    def dataset_name(self):
        return self._dataset_name

    def load(self):
        #TODO curently only the current use case with saved datasets on the disk in a certain format is supported. This should be made more general.
        if self._train_test_exists:
   

            loaded_dts_train = load_from_tsfile_to_dataframe(os.path.join(self._dataset_loc, self._dataset_name + self._suffix_train))
            loaded_dts_test = load_from_tsfile_to_dataframe(os.path.join(self._dataset_loc, self._dataset_name + self._suffix_test))

            data_train = loaded_dts_train[0]
            y_train = loaded_dts_train[1]

            data_test = loaded_dts_test[0]
            y_test = loaded_dts_test[1]

            #concatenate the two dataframes
            data_train[self._target] = y_train
            data_test[self._target] = y_test

            data = pd.concat([data_train,data_test], axis=0, keys=['train','test']).reset_index(level=1, drop=True)

            return data

class DatasetLoadFromDir:
    """
    Loads all datasets in a root directory
    """
    def __init__(self, root_dir):
        """
        Parameters
        ----------
        root_dir: string
            Root directory where the datasets are located
        """
        self._root_dir = root_dir
    
    def load_datasets(self, train_test_exists=True):
        """
        Parameters
        ----------
        train_test_exists: Boolean
            Flag whether the test/train split exists

        Returns
        -------
        DatasetHDD:
            list of DatasetHDD objects
        """
        datasets = os.listdir(self._root_dir)

        data = []
        for dts in datasets:
            dts = DatasetHDD(dataset_loc=os.path.join(self._root_dir, dts), dataset_name=dts, train_test_exists=train_test_exists)
            data.append(dts)
        return data
    
class Result:
    """
    Used for passing results to the analyse results class
    """

    def __init__(self,dataset_name, strategy_name, y_true, y_pred):
        """
        Parameters
        ----------
        dataset_name: string
            Name of the dataset
        strategy_name: string
            name of the strategy
        y_true: list
            True labels
        y_pred: list
            predictions
        """
        self._dataset_name = dataset_name
        self._strategy_name = strategy_name
        self._y_true = y_true
        self._y_pred = y_pred

    @property
    def dataset_name(self):
        return self._dataset_name
    
    @property
    def strategy_name(self):
        return self._strategy_name
    
    @property
    def y_true(self):
        return self._y_true

    @property
    def y_pred(self):
        return self._y_pred

class SKTimeResult(ABC):
    @abstractmethod
    def save(self):
        """
        Saves the result
        """
    @abstractmethod
    def load(self):
        """
        method for loading the results
        """

class ResultHDD(SKTimeResult):
    """
    Class for storing the results of the orchestrator
    """
    def __init__(self, results_save_dir, strategies_save_dir):
        """
        Parameters
        -----------
        results_save_dir: string
            path where the results will be saved
        strategies_save_dir: string
            path for saving the strategies
        """

        self._results_save_dir = results_save_dir
        self._strategies_save_dir = strategies_save_dir

    @property
    def strategies_save_dir(self):
        return self._strategies_save_dir
        
    def save(self, dataset_name, strategy_name, y_true, y_pred, cv_fold):
        """
        Parameters
        ----------
        dataset_name: string
            Name of the dataset
        strategy_name: string
            Name of the strategy
        y_true: array
            True lables array
        y_pred: array
            Predictions array
        cv_fold: int
            Cross validation fold
        """
        if not os.path.exists(self._results_save_dir):
            os.makedirs(self._results_save_dir)
        #TODO BUG: write write_results_to_uea_format does not write the results property unless the probas are provided as well.
        #Dummy probas to make the write_results_to_uea_format function work
        y_true = list(map(int, y_true))
        y_pred = list(map(int, y_pred))
        num_class_true = np.max(y_true)
        num_class_pred = np.max(y_pred)
        num_classes = max(num_class_pred, num_class_true)
        num_predictions = len(y_pred)
        probas = (num_predictions, num_classes)
        probas = np.zeros(probas)

        write_results_to_uea_format(output_path=self._results_save_dir,
                                    classifier_name=strategy_name,
                                    dataset_name=dataset_name,
                                    actual_class_vals=y_true,
                                    predicted_class_vals=y_pred,
                                    actual_probas = probas,
                                    resample_seed=cv_fold)

    
    def load(self):
        """
        Returns
        -------
        list:
            sktime results
        """
        results = []
        for r,d,f in os.walk(self._results_save_dir):
            for file_to_load in f:
                if file_to_load.endswith(".csv"):
                    #found .csv file. Load it and create results object
                    path_to_load = os.path.join(r, file_to_load)
                    current_row= 0
                    strategy_name = ""
                    dataset_name = ""
                    y_true = []
                    y_pred = []
                    with open(path_to_load) as csvfile:
                        readCSV = csv.reader(csvfile, delimiter=',')
                        for row in readCSV:
                            if current_row == 0:
                                strategy_name = row[0]
                                dataset_name = row[1]
                                current_row +=1
                            elif current_row >=4:
                                y_true.append(row[0])
                                y_pred.append(row[1])
                                current_row +=1
                            else:
                                current_row +=1
                    #create result object and append
                    result = Result(dataset_name=dataset_name, strategy_name=strategy_name, y_true=y_true, y_pred=y_pred)
                    results.append(result)
        
        return results
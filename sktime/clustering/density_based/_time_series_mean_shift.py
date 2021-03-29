# -*- coding: utf-8 -*-

__author__ = "Christopher Holder"
__all__ = ["TimeSeriesMeanShift"]


from sktime.clustering._cluster import Cluster
from sktime.clustering.types import Metric_Parameter
from sklearn.cluster import MeanShift


class TimeSeriesMeanShift(Cluster):
    """
    Kmeans clustering algorithm that is built upon the scikit learns
    implementation
    """

    def __init__(
        self,
        bandwidth: float = None,
        seeds: any = None,
        bin_seeding: bool = False,
        min_bin_freq: int = 1,
        cluster_all: bool = True,
        n_jobs: int = None,
        max_iter: int = 300,
        metric: Metric_Parameter = None,
    ):
        super().__init__(
            metric=metric,
        )
        self.model = MeanShift(
            bandwidth=bandwidth,
            seeds=seeds,
            bin_seeding=bin_seeding,
            min_bin_freq=min_bin_freq,
            cluster_all=cluster_all,
            n_jobs=n_jobs,
            max_iter=max_iter,
        )

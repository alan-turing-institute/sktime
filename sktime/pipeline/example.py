# -*- coding: utf-8 -*-
from sktime.pipeline.pipeline import OnlineUnsupervisedPipeline
from sktime.pipeline.transformers import (
    DollarBars,
    CUSUM,
    DailyVol,
    TrippleBarrierEvents,
    TrippleBarrierLabels,
    BuildDataset,
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import BaggingClassifier
from sktime.pipeline.estimators import Estimator

if __name__ == "__main__":
    # simple example
    pipe = OnlineUnsupervisedPipeline(
        steps=[
            ("dollar_bars", DollarBars(), {"X": "original"}),
            ("cusum", CUSUM(price_col="close"), {"input_series": "dollar_bars"}),
            (
                "daily_vol",
                DailyVol(price_col="close", lookback=5),
                {"input_series": "dollar_bars"},
            ),
            (
                "triple_barrier_events",
                TrippleBarrierEvents(price_col="close", num_days=5),
                {
                    "prices": "dollar_bars",
                    "change_points": "cusum",
                    "daily_vol": "daily_vol",
                },
            ),
            (
                "labels",
                TrippleBarrierLabels(price_col="close"),
                {
                    "triple_barrier_events": "triple_barrier_events",
                    "prices": "dollar_bars",
                },
            ),
            (
                "build_dataset",
                BuildDataset(price_col="close", labels_col="bin", lookback=20),
                {"input_dataset": "dollar_bars", "labels": "labels"},
            ),
            (
                "estimator",
                Estimator(
                    estimator=BaggingClassifier(
                        base_estimator=DecisionTreeClassifier(
                            max_depth=5, random_state=1
                        )
                    ),
                    param_grid={
                        "n_estimators": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 25]
                    },
                    samples_col_name="t1",
                    labels_col_name="bin",
                ),
                {
                    "X": "build_dataset",
                    "y": "labels",
                    "samples": "triple_barrier_events",
                },
            ),
        ]
    )
    pipe.fit(X="sktime/pipeline/curated_tick_data.csv")

    # Advance example
    # same pipeline but we define explicitly which function we want to call
    pipeAdvanced = OnlineUnsupervisedPipeline(
        steps=[
            (
                "dollar_bars",
                DollarBars(),
                [
                    {"function": "fit", "arguments": None},
                    {"function": "transform", "arguments": {"X": "original"}},
                ],
            ),
            (
                "cusum",
                CUSUM(price_col="close"),
                [
                    {
                        "function": "transform",
                        "arguments": {"input_series": "dollar_bars"},
                    }
                ],
            ),
            (
                "daily_vol",
                DailyVol(price_col="close", lookback=5),
                [
                    {
                        "function": "transform",
                        "arguments": {"input_series": "dollar_bars"},
                    }
                ],
            ),
            (
                "triple_barrier_events",
                TrippleBarrierEvents(price_col="close", num_days=5),
                [
                    {
                        "function": "transform",
                        "arguments": {
                            "prices": "dollar_bars",
                            "change_points": "cusum",
                            "daily_vol": "daily_vol",
                        },
                    }
                ],
            ),
            (
                "labels",
                TrippleBarrierLabels(price_col="close"),
                [
                    {
                        "function": "transform",
                        "arguments": {
                            "triple_barrier_events": "triple_barrier_events",
                            "prices": "dollar_bars",
                        },
                    }
                ],
            ),
            (
                "build_dataset",
                BuildDataset(price_col="close", labels_col="bin", lookback=20),
                [
                    {
                        "function": "transform",
                        "arguments": {
                            "input_dataset": "dollar_bars",
                            "labels": "labels",
                        },
                    }
                ],
            ),
            (
                "estimator",
                Estimator(
                    estimator=BaggingClassifier(
                        base_estimator=DecisionTreeClassifier(
                            max_depth=5, random_state=1
                        )
                    ),
                    param_grid={
                        "n_estimators": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 25]
                    },
                    samples_col_name="t1",
                    labels_col_name="bin",
                ),
                [
                    {
                        "function": "fit",
                        "arguments": {
                            "X": "build_dataset",
                            "y": "labels",
                            "samples": "triple_barrier_events",
                        },
                    }
                ],
            ),
        ],
        interface="advanced",
    )
    pipeAdvanced.fit(X="sktime/pipeline/curated_tick_data.csv")

#!/usr/bin/env python

# Copyright 2021-2022 NVIDIA Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import math

from benchmark import run_benchmark

try:
    from legate.timing import time
except (ImportError, RuntimeError):
    from time import perf_counter_ns

    def time():
        return perf_counter_ns() / 1000.0


def initialize(N, F, T):
    # We'll generate some random inputs here
    # since we don't need it to converge
    x = np.random.randn(N, F).astype(T, copy=False)
    # Give the results either a 0 or 1 value
    y = np.floor(2.0 * np.random.random(N).astype(T, copy=False))
    return x, y


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def log_likelihood(features, target, weights):
    scores = np.dot(features, weights)
    return np.sum(target * scores - np.log(1.0 + np.exp(scores)))


def logistic_regression(
    T, features, target, steps, learning_rate, sample, add_intercept=False
):
    if add_intercept:
        intercept = np.ones((features.shape[0], 1), dtype=T)
        features = np.hstack((intercept, features))

    weights = np.zeros(features.shape[1], dtype=T)

    for step in range(steps):
        scores = np.dot(features, weights)
        predictions = sigmoid(scores)

        error = target - predictions
        gradient = np.dot(error, features)
        weights += learning_rate * gradient

        if step % sample == 0:
            print(
                "Log Likelihood of step "
                + str(step)
                + ": "
                + str(log_likelihood(features, target, weights))
            )

    return weights


def run_logistic_regression(N, F, T, I, S, B):  # noqa: E741
    print("Running logistic regression...")
    print("Number of data points: " + str(N) + "K")
    print("Number of features: " + str(F))
    print("Number of iterations: " + str(I))
    features, target = initialize(N * 1000, F, T)
    start = time()
    weights = logistic_regression(T, features, target, I, 1e-5, S, B)
    stop = time()
    # Check the weights for NaNs
    assert not math.isnan(np.sum(weights))
    total = (stop - start) / 1000.0
    print(f"Elapsed Time: {total} ms")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b",
        "--intercept",
        dest="B",
        action="store_true",
        help="include an intercept in the calculation",
    )
    parser.add_argument(
        "-f",
        "--features",
        type=int,
        default=32,
        dest="F",
        help="number of features for each input data point",
    )
    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=1000,
        dest="I",
        help="number of iterations to run the algorithm for",
    )
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=10,
        dest="N",
        help="number of elements in the data set in thousands",
    )
    parser.add_argument(
        "-p",
        "--precision",
        type=int,
        default=32,
        dest="P",
        help="precision of the computation in bits",
    )
    parser.add_argument(
        "-s",
        "--sample",
        type=int,
        default=100,
        dest="S",
        help="number of iterations between sampling the log likelihood",
    )
    parser.add_argument(
        "--benchmark",
        type=int,
        default=1,
        dest="benchmark",
        help="number of times to benchmark this application (default 1 - "
        "normal execution)",
    )
    parser.add_argument(
        "--package",
        dest="package",
        choices=["legate", "numpy", "cupy"],
        type=str,
        default="legate",
        help="NumPy package to use (legate, numpy, or cupy)",
    )
    parser.add_argument(
        "--cupy-allocator",
        dest="cupy_allocator",
        choices=["default", "off", "managed"],
        type=str,
        default="default",
        help="cupy allocator to use (default, off, or managed)",
    )

    args, _ = parser.parse_known_args()

    if args.package == "legate":
        import cunumeric as np
    elif args.package == "cupy":
        import cupy as np

        if args.cupy_allocator == "off":
            np.cuda.set_allocator(None)
            print("Turning off memory pool")
        elif args.cupy_allocator == "managed":
            np.cuda.set_allocator(
                np.cuda.MemoryPool(np.cuda.malloc_managed).malloc
            )
            print("Using managed memory pool")
    elif args.package == "numpy":
        import numpy as np

    if args.P == 16:
        run_benchmark(
            run_logistic_regression,
            args.benchmark,
            "LOGREG(H)",
            (args.N, args.F, np.float16, args.I, args.S, args.B),
        )
    elif args.P == 32:
        run_benchmark(
            run_logistic_regression,
            args.benchmark,
            "LOGREG(S)",
            (args.N, args.F, np.float32, args.I, args.S, args.B),
        )
    elif args.P == 64:
        run_benchmark(
            run_logistic_regression,
            args.benchmark,
            "LOGREG(D)",
            (args.N, args.F, np.float64, args.I, args.S, args.B),
        )
    else:
        raise TypeError("Precision must be one of 16, 32, or 64")

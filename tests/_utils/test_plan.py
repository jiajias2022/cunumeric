# Copyright 2022 NVIDIA Corporation
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
"""Provide a TestPlan class to coordinate multiple feature test stages.

"""
from __future__ import annotations

from datetime import timedelta
from itertools import chain

from .config import Config
from .logger import LOG
from .stages import STAGES, log_proc
from .system import System
from .ui import banner, rule, summary, yellow


class TestPlan:
    """Encapsulate an entire test run with multiple feature test stages.

    Parameters
    ----------
    config: Config
        Test runner configuration

    system: System
        Process execution wrapper

    """

    def __init__(self, config: Config, system: System) -> None:
        self._config = config
        self._system = system
        self._stages = [
            STAGES[feature](config, system) for feature in config.features
        ]

    def execute(self) -> int:
        """Execute the entire test run with all configured feature stages."""
        LOG.clear()

        LOG(self.intro)

        for stage in self._stages:
            LOG(stage.intro)
            stage(self._config, self._system)
            LOG(stage.outro)

        all_procs = tuple(
            chain.from_iterable(s.result.procs for s in self._stages)
        )
        total = len(all_procs)
        passed = sum(proc.returncode == 0 for proc in all_procs)

        LOG(f"\n{rule()}")

        self._log_failures(total, passed)

        LOG(self.outro(total, passed))

        return int((total - passed) > 0)

    @property
    def intro(self) -> str:
        """An informative banner to display at test run start."""

        cpus = len(self._system.cpus)
        try:
            gpus = len(self._system.gpus)
        except ImportError:
            gpus = 0

        details = (
            f"* Feature stages       : {', '.join(yellow(x) for x in self._config.features)}",  # noqa E501
            f"* Test files per stage : {yellow(str(len(self._config.test_files)))}",  # noqa E501
            f"* System description   : {yellow(str(cpus) + ' cpus')} / {yellow(str(gpus) + ' gpus')}",  # noqa E501
        )
        return banner("Test Suite Configuration", details=details)

    def outro(self, total: int, passed: int) -> str:
        """An informative banner to display at test run end.

        Parameters
        ----------
        total: int
            Number of total tests that ran in all stages

        passed: int
            Number of tests that passed in all stages

        """
        details = [
            f"* {s.name: <6}: "
            + yellow(
                f"{s.result.passed} / {s.result.total} passed in {s.result.time.total_seconds():0.2f}s"  # noqa E501
            )
            for s in self._stages
        ]

        time = sum((s.result.time for s in self._stages), timedelta(0, 0))
        details.append("")
        details.append(
            summary("All tests", total, passed, time, justify=False)
        )

        overall = banner("Overall summary", details=details)

        return f"{overall}\n"

    def _log_failures(self, total: int, passed: int) -> None:
        if total == passed:
            return

        LOG(f"{banner('FAILURES')}\n")

        for stage in self._stages:
            procs = (proc for proc in stage.result.procs if proc.returncode)
            for proc in procs:
                log_proc(stage.name, proc, self._config, verbose=True)

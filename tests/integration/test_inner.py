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
import pytest
from legate.core import LEGATE_MAX_DIM
from utils.contractions import check_default

from cunumeric.utils import inner_modes


@pytest.mark.parametrize("b_ndim", range(LEGATE_MAX_DIM + 1))
@pytest.mark.parametrize("a_ndim", range(LEGATE_MAX_DIM + 1))
def test_inner(a_ndim, b_ndim):
    name = f"inner({a_ndim} x {b_ndim})"
    modes = inner_modes(a_ndim, b_ndim)

    def operation(lib, *args, **kwargs):
        return lib.inner(*args, **kwargs)

    check_default(name, modes, operation)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(sys.argv))

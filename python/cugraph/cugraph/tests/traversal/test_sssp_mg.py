# Copyright (c) 2020-2023, NVIDIA CORPORATION.
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

import gc

import pytest

import cudf
import cugraph
import dask_cudf
import cugraph.dask as dcg
from cugraph.testing.utils import RAPIDS_DATASET_ROOT_DIR_PATH


# =============================================================================
# Pytest Setup / Teardown - called for each test function
# =============================================================================


def setup_function():
    gc.collect()


IS_DIRECTED = [True, False]


# @pytest.mark.skipif(
#    is_single_gpu(), reason="skipping MG testing on Single GPU system"
# )
@pytest.mark.mg
@pytest.mark.parametrize("directed", IS_DIRECTED)
def test_dask_sssp(dask_client, directed):

    input_data_path = (RAPIDS_DATASET_ROOT_DIR_PATH / "netscience.csv").as_posix()
    print(f"dataset={input_data_path}")
    chunksize = dcg.get_chunksize(input_data_path)

    ddf = dask_cudf.read_csv(
        input_data_path,
        chunksize=chunksize,
        delimiter=" ",
        names=["src", "dst", "value"],
        dtype=["int32", "int32", "float32"],
    )

    df = cudf.read_csv(
        input_data_path,
        delimiter=" ",
        names=["src", "dst", "value"],
        dtype=["int32", "int32", "float32"],
    )

    g = cugraph.Graph(directed=directed)
    g.from_cudf_edgelist(df, "src", "dst", "value", renumber=True)

    dg = cugraph.Graph(directed=directed)
    dg.from_dask_cudf_edgelist(ddf, "src", "dst", "value")

    expected_dist = cugraph.sssp(g, 0)
    print(expected_dist)
    result_dist = dcg.sssp(dg, 0)
    result_dist = result_dist.compute()

    compare_dist = expected_dist.merge(
        result_dist, on="vertex", suffixes=["_local", "_dask"]
    )

    err = 0

    for i in range(len(compare_dist)):
        if (
            compare_dist["distance_local"].iloc[i]
            != compare_dist["distance_dask"].iloc[i]
        ):
            err = err + 1
    assert err == 0

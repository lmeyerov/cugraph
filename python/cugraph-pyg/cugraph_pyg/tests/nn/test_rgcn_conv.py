# Copyright (c) 2023, NVIDIA CORPORATION.
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

import pytest

from cugraph.utilities.utils import import_optional, MissingModule
from cugraph_pyg.nn import RGCNConv as CuGraphRGCNConv

torch_geometric = import_optional("torch_geometric")

ATOL = 1e-6


@pytest.mark.skipif(
    isinstance(torch_geometric, MissingModule), reason="torch_geometric not available"
)
@pytest.mark.parametrize("aggr", ["add", "sum", "mean"])
@pytest.mark.parametrize("bias", [True, False])
@pytest.mark.parametrize("bipartite", [True, False])
@pytest.mark.parametrize("max_num_neighbors", [8, None])
@pytest.mark.parametrize("num_bases", [1, 2, None])
@pytest.mark.parametrize("root_weight", [True, False])
def test_rgcn_conv_equality(
    aggr, bias, bipartite, max_num_neighbors, num_bases, root_weight
):
    import torch
    from torch_geometric.nn import FastRGCNConv as RGCNConv

    in_channels, out_channels, num_relations = (4, 2, 3)
    kwargs = dict(aggr=aggr, bias=bias, num_bases=num_bases, root_weight=root_weight)

    size = (10, 8) if bipartite else (10, 10)
    x = torch.rand(size[0], in_channels, device="cuda")
    edge_index = torch.tensor(
        [
            [7, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 8, 9],
            [0, 1, 2, 3, 4, 5, 6, 7, 7, 7, 7, 7, 7, 7, 7],
        ],
    ).cuda()
    edge_type = torch.tensor([1, 2, 1, 0, 2, 1, 2, 0, 2, 2, 1, 1, 1, 2, 2]).cuda()

    torch.manual_seed(12345)
    conv1 = RGCNConv(in_channels, out_channels, num_relations, **kwargs).cuda()
    torch.manual_seed(12345)
    conv2 = CuGraphRGCNConv(in_channels, out_channels, num_relations, **kwargs).cuda()

    if bipartite:
        out1 = conv1((x, x[: size[1]]), edge_index, edge_type)
    else:
        out1 = conv1(x, edge_index, edge_type)

    csc, edge_type = CuGraphRGCNConv.to_csc(edge_index, size, edge_type)
    out2 = conv2(x, csc, edge_type, max_num_neighbors=max_num_neighbors)
    assert torch.allclose(out1, out2, atol=1e-3)

    grad_out = torch.rand_like(out1)
    out1.backward(grad_out)
    out2.backward(grad_out)

    end = -1 if root_weight else None
    assert torch.allclose(conv1.weight.grad, conv2.weight.grad[:end], atol=1e-3)

    if root_weight:
        assert torch.allclose(conv1.root.grad, conv2.weight.grad[-1], atol=1e-3)

    if num_bases is not None:
        assert torch.allclose(conv1.comp.grad, conv2.comp.grad, atol=1e-3)

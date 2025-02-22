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

from cugraph.utilities.utils import import_optional
from cugraph_dgl.nn import SparseGraph

torch = import_optional("torch")


def test_coo2csc(sparse_graph_1):
    data = sparse_graph_1
    values = torch.ones(data.nnz).cuda()
    g = SparseGraph(
        size=data.size, src_ids=data.src_ids, dst_ids=data.dst_ids, formats="csc"
    )
    cdst_ids, src_ids = g.csc()

    new = torch.sparse_csc_tensor(cdst_ids, src_ids, values).cuda()
    old = torch.sparse_coo_tensor(
        torch.vstack((data.src_ids, data.dst_ids)), values
    ).cuda()
    torch.allclose(new.to_dense(), old.to_dense())


def test_csc2coo(sparse_graph_1):
    data = sparse_graph_1
    values = torch.ones(data.nnz).cuda()
    g = SparseGraph(
        size=data.size,
        src_ids=data.src_ids_sorted_by_dst,
        cdst_ids=data.cdst_ids,
        formats="coo",
    )
    src_ids, dst_ids = g.coo()

    new = torch.sparse_coo_tensor(torch.vstack((src_ids, dst_ids)), values).cuda()
    old = torch.sparse_csc_tensor(
        data.cdst_ids, data.src_ids_sorted_by_dst, values
    ).cuda()
    torch.allclose(new.to_dense(), old.to_dense())

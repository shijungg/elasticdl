# Copyright 2020 The ElasticDL Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple

import numpy as np
from tensorflow.core.framework import tensor_pb2

from elasticdl.proto import elasticdl_pb2
from elasticdl.python.common.dtypes import (
    dtype_numpy_to_tensor,
    dtype_tensor_to_numpy,
)

Tensor = namedtuple("Tensor", ("name", "values", "indices"))
EmbeddingTableInfo = namedtuple(
    "EmbeddingTableInfo", ("name", "dim", "initializer", "dtype")
)


def merge_indexed_slices(*args):
    return Tensor(
        name=None,
        values=np.concatenate([i.values for i in args], axis=0),
        indices=np.concatenate([i.indices for i in args], axis=0),
    )


def deduplicate_indexed_slices(values, indices):
    """
    Sum up the values associated with duplicated indices and
    return unique indices with corresponding summed values.
    Args:
        values: A Tensor with rank >= 1.
        indices: A one-dimension integer of Tensor.
    Returns:
        A tuple of (`sum_combined_values`, `unique_indices`).
        `sum_combined_values` contains the sum of `values` associated
        with each unique indice.
        `unique_indices` is a de-duplicated version of `indices`.
    """

    res = {}
    for index, i in enumerate(indices.tolist()):
        if i not in res:
            res[i] = values[index, :]
        else:
            res[i] += values[index, :]

    return np.stack(res.values()), np.asarray(res.keys())


def serialize_ndarray(array, pb):
    dtype = dtype_numpy_to_tensor(array.dtype)
    if not dtype:
        raise ValueError("Dtype of ndarray %s is not supported", array.dtype)
    pb.dtype = dtype
    pb.tensor_content = array.tobytes()
    for d in array.shape:
        pb_d = pb.tensor_shape.dim.add()
        pb_d.size = d


def ndarray_to_pb(array):
    pb = tensor_pb2.TensorProto()
    serialize_ndarray(array, pb)
    return pb


def pb_to_ndarray(pb):
    if not pb.tensor_shape:
        raise ValueError("PB has no dim defined")
    dtype = dtype_tensor_to_numpy(pb.dtype)
    size = dtype.itemsize
    shape = [d.size for d in pb.tensor_shape.dim]
    for d in shape:
        size *= d
    if size != len(pb.tensor_content):
        raise ValueError(
            "PB size mismatch, dim: %s, len(content): %d",
            str(shape),
            len(pb.tensor_content),
        )
    array = np.ndarray(shape=shape, dtype=dtype, buffer=pb.tensor_content)
    return array


def pb_to_indexed_slices(pb):
    concat_tensors = pb_to_ndarray(pb.concat_tensors)
    ids = np.array([int(i) for i in pb.ids])
    return Tensor(None, concat_tensors, ids)


def serialize_indexed_slices(slices, pb):
    serialize_ndarray(slices.values, pb.concat_tensors)
    indices = slices.indices
    if isinstance(indices, np.ndarray):
        if len(indices.shape) > 1:
            raise ValueError(
                "IndexedSlices pb only accepts indices with one "
                "dimension, got %d",
                len(indices.shape),
            )
        else:
            indices = indices.tolist()
    pb.ids.extend(indices)


def indexed_slices_to_pb(slices):
    pb = elasticdl_pb2.IndexedSlicesProto()
    serialize_indexed_slices(slices, pb)
    return pb

# Issue

**Title:** BUG: BPTree GPU dispatch: out-of-memory fallback, device selection, and probe caching

## Description

# Summary

This PR fixes three behaviours of `BPTree`'s GPU dispatch, the code that sends the batch operations and `cophenet` of a tree on a GPU to the Numba GPU kernels:

- A single call that ran out of device memory turned the GPU off for the rest of the process.
- Every call probed for the Numba GPU extension several times over, each time re-trying the import of an extension that is not installed.
- The kernels ran on GPU 0, whatever GPU the tree is on.

## Main Changes

### 1. Running out of device memory turned the GPU off

**Problem**

- When a GPU kernel raises, the batch operations and `cophenet` call `_mark_gpu_unavailable`, which routes that backend (CuPy or PyTorch) to the CPU engines for the rest of the process. That is right for a kernel that cannot build or run on the system.
- Running out of device memory, though, is a property of one call, e.g. a batch of queries, or a tree's index, larger than the free memory. It was handled the same way, so after one such call every later batch and `cophenet` call on any CuPy or PyTorch tree ran on the CPU, small ones included.

**Fix**

- An out-of-memory error is now told apart from other failures. That call is computed on the CPU with a warning, and later calls still use the GPU.
- Each library raises its own error, so the error is matched by type and message:

  | Library | Out-of-memory error |
  |---|---|
  | CuPy | `MemoryError` (`OutOfMemoryError`) |
  | PyTorch | `torch.OutOfMemoryError` ("CUDA out of memory") |
  | numba-cuda, numba-cuda-mlir | `CudaAPIError` naming `CUDA_ERROR_OUT_OF_MEMORY` |
  | numba-hip (ROCm, not tested) | `hipErrorOutOfMemory` |

- Allocations made outside the kernel call, i.e. the result of a batch on the queries' device and the `cophenet` matrix, still raise their error, as before.

### 2. The GPU extension was probed on every call

**Problem**

- Each batch operation and `cophenet` worked out what `engine="fast"` would mean even when another engine was asked for, and did so again for each kernel it ran (3 per `cophenet`).
- On a GPU tree, that means probing for the Numba GPU module, which tries to import each GPU extension in turn. Python does not remember a failed import, so the extension that is not installed (`numba_cuda_mlir` beside numba-cuda) was searched for again on every probe. With numba-cuda, this probe took about 22 µs, several times per call.

**Fix**

- The engine is resolved once per call, and what `"fast"` means is worked out only when `engine="fast"` is asked for.
- The probe is cached for the process, as what is installed does not change within it. Kernels that failed are still checked on every call, so a backend whose kernels cannot run still goes to the CPU.

### 3. The kernels ran on GPU 0, not on the tree's GPU

**Problem**

- The batch operations and `cophenet` uploaded the tree's index, and launched their kernels, on the current device of the Numba GPU module, which is device 0 unless selected.
- A tree on another GPU, e.g. made with `to_device(cupy, 1)` or from a tensor on `cuda:1`, had its index uploaded to GPU 0 and its kernels run there, on queries and an output in the memory of GPU 1. The result is an illegal memory access, which can leave the GPU context unusable, or a fallback that turns the GPU off for the process.
- `numba_arrays(gpu=...)` also uploaded to GPU 0.

**Fix**

- The tree's GPU (CuPy's device id, PyTorch's device index, or PyTorch's current device for `"cuda"`) is made the Numba module's current device for the upload of the index, each batch, and `cophenet`'s kernel.
- `numba_arrays(gpu=...)` of a tree on a GPU uploads to that GPU.
- Queries on a GPU other than the tree's raise `ValueError`, as array API operations on arrays of different devices do.
- A tree on the host keeps the module's current device.

## Performance and memory

Two A/B comparisons against `bp_tree`:
- **Small calls**, where the probing removed in change 2 is a large share of each call;
- **the full benchmark** used for the o

…(truncated)

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `e6f51b1ef6de` and running the modified tests.
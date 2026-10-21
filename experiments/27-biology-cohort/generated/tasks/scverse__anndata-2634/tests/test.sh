#!/bin/bash
set -uxo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /workspace
git config --global --add safe.directory /workspace
mkdir -p /logs/verifier
git checkout d75540e9136f3440d5e20be53da69e987bf463a7 -- src/anndata/tests/helpers.py tests/conftest.py tests/lazy/conftest.py tests/lazy/test_concat.py tests/lazy/test_read.py tests/test_annot.py tests/test_backed_dense.py tests/test_backed_sparse.py tests/test_base.py tests/test_concatenate_disk.py tests/test_dask.py tests/test_gpu.py tests/test_io_backwards_compat.py tests/test_io_dispatched.py tests/test_io_elementwise.py tests/test_io_partial.py tests/test_io_utils.py tests/test_readwrite.py tests/test_structured_arrays.py tests/test_x.py tests/test_x_layers_2d.py || true
git apply --verbose --reject - <<'EOF_R2E_TEST_PATCH'
diff --git a/src/anndata/tests/helpers.py b/src/anndata/tests/helpers.py
index c1195c715..bac800d4b 100644
--- a/src/anndata/tests/helpers.py
+++ b/src/anndata/tests/helpers.py
@@ -20,7 +20,9 @@
 from pandas.api.types import is_numeric_dtype
 from pandas.core.arrays.integer import IntegerDtype
 from scipy import sparse
-from zarr.storage import LocalStore
+from zarr.abc.store import Store
+from zarr.core.buffer import default_buffer_prototype
+from zarr.storage import MemoryStore, WrapperStore
 
 from anndata import AnnData, ExperimentalFeatureWarning, Raw
 from anndata._core.aligned_mapping import AlignedMappingBase
@@ -45,6 +47,7 @@
 
 if TYPE_CHECKING:
     from collections.abc import Callable, Collection, Iterable, MutableMapping
+    from pathlib import Path
     from types import ModuleType
     from typing import Any, Literal, TypeGuard
 
@@ -1241,13 +1244,41 @@ def shares_memory_sparse(x, y):
 ]
 
 
-class AccessTrackingStore(LocalStore):
+@overload
+def open_store(store: Path, /, mode: Literal["r", "a"] = "a") -> h5py.File: ...
+@overload
+def open_store(store: MemoryStore, /, mode: Literal["r", "a"] = "a") -> zarr.Group: ...
+def open_store(
+    store: Path | MemoryStore, /, mode: Literal["r", "a"] = "a"
+) -> h5py.File | zarr.Group:
+    """Open a `diskfmt_store`: a `Path` for h5, a `MemoryStore` for zarr."""
+    if not isinstance(store, MemoryStore):
+        return h5py.File(store, mode)
+    from anndata._io.zarr import open_write_group
+
+    return (
+        open_write_group(store, mode=mode)
+        if mode == "a"
+        else zarr.open_group(store, mode=mode)
+    )
+
+
+class AccessTrackingStore(WrapperStore[Store]):
+    """Wraps a store to count reads of (prefixes of) keys.
+
+    Wrap the store a fixture wrote to, e.g. ``AccessTrackingStore(store)``,
+    to get a fresh set of counters over the same data.
+
+    The wrapper is always read-only: `zarr` re-wraps a writable store when
+    opened with ``mode="r"``, which would silently reset the counters.
+    """
+
     _access_count: Counter[str]
     _accessed: defaultdict[str, set]
     _accessed_keys: defaultdict[str, list[str]]
 
-    def __init__(self, *args, **kwargs):
-        super().__init__(*args, **kwargs)
+    def __init__(self, store: Store) -> None:
+        super().__init__(store.with_read_only(read_only=True))
         self._access_count = Counter()
         self._accessed = defaultdict(set)
         self._accessed_keys = defaultdict(list)
@@ -1271,7 +1302,9 @@ async def get(
         byte_range: ByteRequest | None = None,
     ) -> Buffer | None:
         self._check_and_track_key(key)
-        return await super().get(key, prototype=prototype, byte_range=byte_range)
+        if prototype is None:  # concrete stores default it, the ABC does not
+            prototype = default_buffer_prototype()
+        return await self._store.get(key, prototype, byte_range)
 
     def _check_and_track_key(self, key: str):
         for tracked in self._access_count:
diff --git a/tests/conftest.py b/tests/conftest.py
index f7a6612ce..b78893cda 100644
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -18,6 +18,7 @@
 
 from filelock import FileLock
 from scipy import sparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata.tests.helpers import subset_func  # noqa: F401
@@ -75,6 +76,28 @@ def diskfmt2(
         yield "h5ad"
 
 
+def _store_for(tmp_path: Path, diskfmt: str, name: str) -> Path | MemoryStore:
+    """Where to write: a file path for `h5ad`, an in-memory store for `zarr`.
+
+    Tests should not touch the file system unless that is what they test.
+    """
+    return tmp_path / f"{name}.h5ad" if diskfmt == "h5ad" else MemoryStore()
+
+
+@pytest.fixture
+def diskfmt_store(
+    tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]
+) -> Path | MemoryStore:
+    return _store_for(tmp_path, diskfmt, "test")
+
+
+@pytest.fixture
+def diskfmt2_store(
+    tmp_path: Path, diskfmt2: Literal["h5ad", "zarr"]
+) -> Path | MemoryStore:
+    return _store_for(tmp_path, diskfmt2, "test2")
+
+
 @pytest.fixture(
     params=[
         pytest.param((..., (slice(None), slice(None))), id="ellipsis"),
diff --git a/tests/lazy/conftest.py b/tests/lazy/conftest.py
index 01983b876..5cb8b43df 100644
--- a/tests/lazy/conftest.py
+++ b/tests/lazy/conftest.py
@@ -7,6 +7,7 @@
 import pytest
 import zarr
 from scipy import sparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata import AnnData
@@ -73,18 +74,17 @@ def simple_subset_func(request):
 
 
 @pytest.fixture(scope="session")
-def adata_remote_orig_with_path(
+def adata_remote_orig_with_store(
     tmp_path_factory,
     diskfmt: str,
     mtx_format,
     worker_id: str = "serial",
-) -> tuple[Path, AnnData]:
+) -> tuple[Path | MemoryStore, AnnData]:
     """Create remote fixtures, one without a range index and the other with"""
-    file_name = f"orig_{worker_id}.{diskfmt}"
     if diskfmt == "h5ad":
-        orig_path = tmp_path_factory.mktemp("h5ad_file_dir") / file_name
+        orig_store = tmp_path_factory.mktemp("h5ad_file_dir") / f"orig_{worker_id}.h5ad"
     else:
-        orig_path = tmp_path_factory.mktemp(file_name)
+        orig_store = MemoryStore()
     orig = gen_adata(
         (100, 110),
         mtx_format,
@@ -96,32 +96,32 @@ def adata_remote_orig_with_path(
     orig.raw = orig.copy()
     with ad.settings.override(allow_write_nullable_strings=True):
         getattr(ad.io, f"write_{diskfmt}")(
-            orig_path, orig, convert_strings_to_categoricals=False
+            orig_store, orig, convert_strings_to_categoricals=False
         )
-    return orig_path, orig
+    return orig_store, orig
 
 
 @pytest.fixture
 def adata_remote(
-    adata_remote_orig_with_path: tuple[Path, AnnData], *, load_annotation_index: bool
+    adata_remote_orig_with_store: tuple[Path | MemoryStore, AnnData],
+    *,
+    load_annotation_index: bool,
 ) -> AnnData:
-    orig_path, _ = adata_remote_orig_with_path
-    return read_lazy(orig_path, load_annotation_index=load_annotation_index)
+    orig_store, _ = adata_remote_orig_with_store
+    return read_lazy(orig_store, load_annotation_index=load_annotation_index)
 
 
 @pytest.fixture
-def adata_orig(adata_remote_orig_with_path: tuple[Path, AnnData]) -> AnnData:
-    _, orig = adata_remote_orig_with_path
+def adata_orig(
+    adata_remote_orig_with_store: tuple[Path | MemoryStore, AnnData],
+) -> AnnData:
+    _, orig = adata_remote_orig_with_store
     return orig
 
 
 @pytest.fixture(scope="session", params=[pytest.param(None, marks=pytest.mark.zarr_io)])
-def adata_remote_with_store_tall_skinny_path(
-    tmp_path_factory,
-    mtx_format,
-    worker_id: str = "serial",
-) -> Path:
-    orig_path = tmp_path_factory.mktemp(f"orig_{worker_id}.zarr")
+def adata_remote_tall_skinny_orig_store(mtx_format) -> MemoryStore:
+    orig_store = MemoryStore()
     M = 1000
     N = 5
     # One named, one unnamed
@@ -135,8 +135,8 @@ def adata_remote_with_store_tall_skinny_path(
         X=mtx_format(np.random.binomial(100, 0.005, (M, N)).astype(np.float32)),
     )
     orig.raw = orig.copy()
-    orig.write_zarr(orig_path)
-    g = zarr.open_group(orig_path, mode="a", use_consolidated=False)
+    orig.write_zarr(orig_store)
+    g = zarr.open_group(orig_store, mode="a", use_consolidated=False)
     ad.io.write_elem(
         g,
         "obs",
@@ -150,22 +150,22 @@ def adata_remote_with_store_tall_skinny_path(
         match=r"Consolidated metadata",
     ):
         zarr.consolidate_metadata(g.store)
-    return orig_path
+    return orig_store
 
 
 @pytest.fixture(scope="session", params=[pytest.param(None, marks=pytest.mark.zarr_io)])
-def adatas_paths_var_indices_for_concatenation(
-    tmp_path_factory, *, are_vars_different: bool, worker_id: str = "serial"
-) -> tuple[list[AnnData], list[Path], list[pd.Index]]:
+def adatas_stores_var_indices_for_concatenation(
+    *, are_vars_different: bool
+) -> tuple[list[AnnData], list[MemoryStore], list[pd.Index]]:
     adatas = []
     var_indices = []
-    paths = []
+    stores = []
     M = 1000
     N = 50
     n_datasets = 3
     for dataset_index in range(n_datasets):
-        orig_path = tmp_path_factory.mktemp(f"orig_{worker_id}_{dataset_index}.zarr")
-        paths.append(orig_path)
+        orig_store = MemoryStore()
+        stores.append(orig_store)
         obs_names = pd.Index(f"cell_{dataset_index}_{i}" for i in range(M))
         var_names = pd.Index(
             f"gene_{i}{f'_{dataset_index}_ds' if are_vars_different and (i % 2) else ''}"
@@ -179,33 +179,33 @@ def adatas_paths_var_indices_for_concatenation(
             var=var,
             X=np.random.binomial(100, 0.005, (M, N)).astype(np.float32),
         )
-        orig.write_zarr(orig_path)
+        orig.write_zarr(orig_store)
         adatas.append(orig)
-    return adatas, paths, var_indices
+    return adatas, stores, var_indices
 
 
 @pytest.fixture
 def var_indices_for_concat(
-    adatas_paths_var_indices_for_concatenation,
+    adatas_stores_var_indices_for_concatenation,
 ) -> list[pd.Index]:
-    _, _, var_indices = adatas_paths_var_indices_for_concatenation
+    _, _, var_indices = adatas_stores_var_indices_for_concatenation
     return var_indices
 
 
 @pytest.fixture
 def adatas_for_concat(
-    adatas_paths_var_indices_for_concatenation,
+    adatas_stores_var_indices_for_concatenation,
 ) -> list[AnnData]:
-    adatas, _, _ = adatas_paths_var_indices_for_concatenation
+    adatas, _, _ = adatas_stores_var_indices_for_concatenation
     return adatas
 
 
 @pytest.fixture
 def stores_for_concat(
-    adatas_paths_var_indices_for_concatenation,
+    adatas_stores_var_indices_for_concatenation,
 ) -> list[AccessTrackingStore]:
-    _, paths, _ = adatas_paths_var_indices_for_concatenation
-    return [AccessTrackingStore(path, read_only=True) for path in paths]
+    _, stores, _ = adatas_stores_var_indices_for_concatenation
+    return [AccessTrackingStore(store) for store in stores]
 
 
 @pytest.fixture
@@ -220,20 +220,18 @@ def lazy_adatas_for_concat(
 
 @pytest.fixture
 def adata_remote_with_store_tall_skinny(
-    adata_remote_with_store_tall_skinny_path: Path,
+    adata_remote_tall_skinny_orig_store: MemoryStore,
 ) -> tuple[AnnData, AccessTrackingStore]:
-    store = AccessTrackingStore(
-        adata_remote_with_store_tall_skinny_path, read_only=True
-    )
+    store = AccessTrackingStore(adata_remote_tall_skinny_orig_store)
     remote = read_lazy(store)
     return remote, store
 
 
 @pytest.fixture
 def remote_store_tall_skinny(
-    adata_remote_with_store_tall_skinny_path: Path,
+    adata_remote_tall_skinny_orig_store: MemoryStore,
 ) -> AccessTrackingStore:
-    return AccessTrackingStore(adata_remote_with_store_tall_skinny_path, read_only=True)
+    return AccessTrackingStore(adata_remote_tall_skinny_orig_store)
 
 
 @pytest.fixture
diff --git a/tests/lazy/test_concat.py b/tests/lazy/test_concat.py
index 308a86e7a..7ddb87f5c 100644
--- a/tests/lazy/test_concat.py
+++ b/tests/lazy/test_concat.py
@@ -7,6 +7,7 @@
 import numpy as np
 import pandas as pd
 import pytest
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata._core.file_backing import to_memory
@@ -18,7 +19,6 @@
 
 if TYPE_CHECKING:
     from collections.abc import Callable, Generator
-    from pathlib import Path
     from typing import Literal
 
     from numpy.typing import NDArray
@@ -344,10 +344,10 @@ def with_elem_in_memory(adata: AnnData, attr: str, key: str | None) -> AnnData:
     assert_equal(mixed_concatenated, in_memory_concatenated)
 
 
-def test_concat_bad_mixed_types(tmp_path: Path):
+def test_concat_bad_mixed_types():
     orig = gen_adata((100, 200), np.array, **GEN_ADATA_NO_XARRAY_ARGS)
-    orig.write_zarr(tmp_path)
-    remote = read_lazy(tmp_path)
+    orig.write_zarr(store := MemoryStore())
+    remote = read_lazy(store)
     orig.obsm["df"] = orig.obsm["array"]
     with pytest.raises(ValueError, match=r"Cannot concatenate a Dataset2D*"):
         ad.concat([remote, orig], join="outer")
diff --git a/tests/lazy/test_read.py b/tests/lazy/test_read.py
index 3a8f731a6..059cd082f 100644
--- a/tests/lazy/test_read.py
+++ b/tests/lazy/test_read.py
@@ -1,21 +1,20 @@
 from __future__ import annotations
 
-import json
 from importlib.util import find_spec
-from pathlib import Path
 from typing import TYPE_CHECKING
 
 import numpy as np
 import pandas as pd
 import pytest
 import zarr
+from zarr.storage import MemoryStore
 
 from anndata import AnnData
 from anndata._core.xarray import Dataset2D
 from anndata.compat import DaskArray
 from anndata.experimental import read_elem_lazy, read_lazy
 from anndata.experimental.backed._io import ANNDATA_ELEMS
-from anndata.io import read_zarr, write_elem
+from anndata.io import read_zarr, write_elem, write_zarr
 from anndata.tests.helpers import (
     GEN_ADATA_NO_XARRAY_ARGS,
     AccessTrackingStore,
@@ -26,6 +25,7 @@
 
 if TYPE_CHECKING:
     from collections.abc import Callable
+    from pathlib import Path
 
     from anndata._types import AnnDataElem
 
@@ -92,9 +92,9 @@ def test_access_count_subset_column_compute(
 
 def test_access_count_index(
     remote_store_tall_skinny: AccessTrackingStore,
-    adata_remote_with_store_tall_skinny_path: Path,
+    adata_remote_tall_skinny_orig_store: MemoryStore,
 ) -> None:
-    adata_orig = read_zarr(adata_remote_with_store_tall_skinny_path)
+    adata_orig = read_zarr(adata_remote_tall_skinny_orig_store)
 
     remote_store_tall_skinny.initialize_key_trackers(["obs/obs_names"])
     read_lazy(remote_store_tall_skinny, load_annotation_index=False)
@@ -111,7 +111,7 @@ def test_access_count_index(
 def test_access_count_dtype(
     remote_store_tall_skinny: AccessTrackingStore,
     adata_remote_tall_skinny: AnnData,
-    adata_remote_with_store_tall_skinny_path: Path,
+    adata_remote_tall_skinny_orig_store: MemoryStore,
 ) -> None:
 
     remote_store_tall_skinny.initialize_key_trackers(["obs/cat/categories"])
@@ -150,7 +150,7 @@ def test_to_memory(adata_remote: AnnData, adata_orig: AnnData):
     assert_equal(remote_to_memory, adata_orig)
 
 
-def test_access_counts_obsm_df(tmp_path: Path):
+def test_access_counts_obsm_df():
     adata = AnnData(
         X=np.array(np.random.rand(100, 20)),
     )
@@ -158,8 +158,8 @@ def test_access_counts_obsm_df(tmp_path: Path):
         {"col1": np.random.rand(100), "col2": np.random.rand(100)},
         index=adata.obs_names,
     )
-    adata.write_zarr(tmp_path)
-    store = AccessTrackingStore(tmp_path, read_only=True)
+    adata.write_zarr(orig_store := MemoryStore())
+    store = AccessTrackingStore(orig_store)
     store.initialize_key_trackers(["obsm/df"])
     read_lazy(store, load_annotation_index=False)
     store.assert_access_count("obsm/df", 0)
@@ -202,17 +202,11 @@ def test_view_of_view_to_memory(adata_remote: AnnData, adata_orig: AnnData):
 
 
 @pytest.mark.zarr_io
-def test_unconsolidated(tmp_path: Path, mtx_format):
+def test_unconsolidated(mtx_format):
     adata = gen_adata((10, 10), mtx_format, **GEN_ADATA_NO_XARRAY_ARGS)
-    orig_pth = tmp_path / "orig.zarr"
-    adata.write_zarr(orig_pth)
-    with Path.open(orig_pth / "zarr.json", "r+") as f:
-        data = json.load(f)
-        del data["consolidated_metadata"]
-        f.seek(0)
-        json.dump(data, f)
-        f.truncate()
-    store = AccessTrackingStore(orig_pth, read_only=True)
+    orig_store = MemoryStore()
+    write_zarr(orig_store, adata, consolidate_metadata=False)
+    store = AccessTrackingStore(orig_store)
     store.initialize_key_trackers(["obs/zarr.json", "zarr.json"])
     with pytest.warns(UserWarning, match=r"Did not read zarr as consolidated"):
         remote = read_lazy(store)
@@ -222,11 +216,10 @@ def test_unconsolidated(tmp_path: Path, mtx_format):
 
 
 @pytest.mark.zarr_io
-def test_empty_df_warns(tmp_path: Path):
+def test_empty_df_warns():
     adata = AnnData(X=np.ones((10, 10)))
-    zarr_path = tmp_path / "orig.zarr"
-    adata.write_zarr(zarr_path)
-    root = zarr.open(zarr_path)
+    adata.write_zarr(store := MemoryStore())
+    root = zarr.open(store)
     assert isinstance(root, zarr.Group)
     obs = read_elem_lazy(root["obs"])
     assert isinstance(obs, Dataset2D)
@@ -248,12 +241,12 @@ def test_h5_file_obj(tmp_path: Path):
 
 
 @pytest.fixture(scope="session")
-def df_group(tmp_path_factory) -> zarr.Group:
+def df_group() -> zarr.Group:
     df = gen_typed_df(120)
-    path = tmp_path_factory.mktemp("foo.zarr")
-    g = zarr.open_group(path, mode="w", zarr_format=2)
+    store = MemoryStore()
+    g = zarr.open_group(store, mode="w", zarr_format=2)
     write_elem(g, "foo", df, dataset_kwargs={"chunks": 25})
-    foo = zarr.open_group(path, mode="r")["foo"]
+    foo = zarr.open_group(store, mode="r")["foo"]
     assert isinstance(foo, zarr.Group)
     return foo
 
@@ -264,7 +257,6 @@ def df_group(tmp_path_factory) -> zarr.Group:
     ids=["small", "minus_one_uses_full", "none_uses_ondisk_chunking"],
 )
 def test_chunks_df(
-    tmp_path: Path,
     chunks: tuple[int] | None,
     expected_chunks: tuple[int],
     df_group: zarr.Group,
diff --git a/tests/test_annot.py b/tests/test_annot.py
index 8f131fbe1..867524bee 100644
--- a/tests/test_annot.py
+++ b/tests/test_annot.py
@@ -3,22 +3,19 @@
 from __future__ import annotations
 
 from contextlib import nullcontext
-from typing import TYPE_CHECKING
 
 import numpy as np
 import pandas as pd
 import pyarrow as pa
 import pytest
 from natsort import natsorted
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata._io.specs.registry import IORegistryError
 from anndata._warnings import ImplicitModificationWarning
 from anndata.tests.helpers import assert_equal, get_multiindex_columns_df
 
-if TYPE_CHECKING:
-    from pathlib import Path
-
 
 @pytest.mark.parametrize("dtype", [object, "string"])
 def test_str_to_categorical(dtype):
@@ -161,7 +158,7 @@ def test_arrow_index(restrict_index_types):
         )
 
 
-def test_arrow_index_write(tmp_path: Path):
+def test_arrow_index_write():
     ad.settings.restrict_index_types = False
     # See: https://github.com/pandas-dev/pandas/issues/64889 for why we can't just use dicts/lists in the arrow extension array
     arr = pa.array(
@@ -183,7 +180,7 @@ def test_arrow_index_write(tmp_path: Path):
         IORegistryError,
         match=r"No method registered for writing <class 'pandas",
     ):
-        adata.write_zarr(tmp_path / "adata.zarr")
+        adata.write_zarr(MemoryStore())
 
 
 @pytest.mark.parametrize(
diff --git a/tests/test_backed_dense.py b/tests/test_backed_dense.py
index 62cf32415..7770ef545 100644
--- a/tests/test_backed_dense.py
+++ b/tests/test_backed_dense.py
@@ -10,23 +10,19 @@
 import zarr
 
 from anndata import AnnData
-from anndata._io.zarr import open_write_group
 from anndata.io import write_elem
-from anndata.tests.helpers import assert_equal
+from anndata.tests.helpers import assert_equal, open_store
 
 if TYPE_CHECKING:
     from pathlib import Path
     from typing import Literal
 
+    from zarr.storage import MemoryStore
+
 
 @pytest.fixture
-def file(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]) -> h5py.File | zarr.Group:
-    path = tmp_path / f"test.{diskfmt}"
-    if diskfmt == "zarr":
-        return open_write_group(path, mode="a")
-    if diskfmt == "h5ad":
-        return h5py.File(path, "a")
-    pytest.fail(f"Unknown diskfmt: {diskfmt}")
+def file(diskfmt_store: Path | MemoryStore) -> h5py.File | zarr.Group:
+    return open_store(diskfmt_store)
 
 
 @pytest.mark.parametrize("assign", ["init", "assign"])
diff --git a/tests/test_backed_sparse.py b/tests/test_backed_sparse.py
index d1ec4f0c8..eb9f270a2 100644
--- a/tests/test_backed_sparse.py
+++ b/tests/test_backed_sparse.py
@@ -10,6 +10,7 @@
 import pytest
 import zarr
 from scipy import sparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata._core.anndata import AnnData
@@ -20,7 +21,12 @@
 from anndata.compat import CSArray, CSMatrix, DaskArray
 from anndata.experimental import read_dispatched
 from anndata.tests import helpers as test_helpers
-from anndata.tests.helpers import AccessTrackingStore, assert_equal, subset_func
+from anndata.tests.helpers import (
+    AccessTrackingStore,
+    assert_equal,
+    open_store,
+    subset_func,
+)
 from anndata.utils import get_literal_members
 
 if TYPE_CHECKING:
@@ -64,9 +70,10 @@ def zarr_separator():
 def ondisk_equivalent_adata(
     tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]
 ) -> tuple[AnnData, AnnData, AnnData, AnnData]:
-    csr_path = tmp_path / f"csr.{diskfmt}"
-    csc_path = tmp_path / f"csc.{diskfmt}"
-    dense_path = tmp_path / f"dense.{diskfmt}"
+    make_store = lambda name: (
+        tmp_path / f"{name}.h5ad" if diskfmt == "h5ad" else MemoryStore()
+    )
+    csr_store, csc_store, dense_store = map(make_store, ["csr", "csc", "dense"])
 
     write = lambda x, pth, **kwargs: getattr(x, f"write_{diskfmt}")(pth, **kwargs)
 
@@ -75,20 +82,19 @@ def ondisk_equivalent_adata(
     csc_mem = ad.AnnData(X=csr_mem.X.tocsc())
     dense_mem = ad.AnnData(X=csr_mem.X.toarray())
 
-    write(csr_mem, csr_path)
-    write(csc_mem, csc_path)
-    # write(csr_mem, dense_path, as_dense="X")
-    write(dense_mem, dense_path)
+    write(csr_mem, csr_store)
+    write(csc_mem, csc_store)
+    # write(csr_mem, dense_store, as_dense="X")
+    write(dense_mem, dense_store)
     if diskfmt == "h5ad":
-        csr_disk = ad.read_h5ad(csr_path, backed="r")
-        csc_disk = ad.read_h5ad(csc_path, backed="r")
-        dense_disk = ad.read_h5ad(dense_path, backed="r")
+        csr_disk, csc_disk, dense_disk = (
+            ad.read_h5ad(cast("Path", store), backed="r")
+            for store in [csr_store, csc_store, dense_store]
+        )
     else:
 
-        def read_zarr_backed(path):
-            path = str(path)
-
-            f = zarr.open(path, mode="r")
+        def read_zarr_backed(store):
+            f = zarr.open(store, mode="r")
 
             # Read with handling for backwards compat
             def callback(func, elem_name, elem, iospec):
@@ -104,9 +110,9 @@ def callback(func, elem_name, elem, iospec):
 
             return adata
 
-        csr_disk = read_zarr_backed(csr_path)
-        csc_disk = read_zarr_backed(csc_path)
-        dense_disk = read_zarr_backed(dense_path)
+        csr_disk = read_zarr_backed(csr_store)
+        csc_disk = read_zarr_backed(csc_store)
+        dense_disk = read_zarr_backed(dense_store)
 
     return csr_mem, csr_disk, csc_disk, dense_disk
 
@@ -292,15 +298,13 @@ def test_consecutive_bool(
     ],
 )
 def test_dataset_append_memory(
-    tmp_path: Path,
+    diskfmt_store: Path | MemoryStore,
     sparse_format: type[CSMatrix | CSArray],
     append_method: Callable[[list[CSMatrix | CSArray]], CSMatrix | CSArray],
-    diskfmt: Literal["h5ad", "zarr"],
 ):
-    path = tmp_path / f"test.{diskfmt.replace('ad', '')}"
     a = sparse_format(sparse.random(100, 100))
     b = sparse_format(sparse.random(100, 100))
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
     ad.io.write_elem(f, "mtx", a)
     diskmtx = sparse_dataset(subgroup(f, "mtx"))
     assert isinstance(diskmtx, BaseCompressedSparseDataset)
@@ -313,10 +317,9 @@ def test_dataset_append_memory(
     assert_equal(fromdisk, frommem)
 
 
-def test_append_array_cache_bust(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]):
-    path = tmp_path / f"test.{diskfmt.replace('ad', '')}"
+def test_append_array_cache_bust(diskfmt_store: Path | MemoryStore):
     a = sparse.random(100, 100, format="csr")
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
     ad.io.write_elem(f, "mtx", a)
     ad.io.write_elem(f, "mtx_2", a)
     diskmtx = sparse_dataset(subgroup(f, "mtx"))
@@ -344,17 +347,15 @@ def test_append_array_cache_bust(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"
     ),
 )
 def test_read_array(
-    tmp_path: Path,
+    diskfmt_store: Path | MemoryStore,
     sparse_format: type[CSMatrix],
-    diskfmt: Literal["h5ad", "zarr"],
     subset_func,
     subset_func2,
 ):
-    path = tmp_path / f"test.{diskfmt.replace('ad', '')}"
     a = sparse_format(sparse.random(100, 100))
     obs_idx = subset_func(np.arange(100))
     var_idx = subset_func2(np.arange(100))
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
     ad.io.write_elem(f, "mtx", a)
     diskmtx = sparse_dataset(subgroup(f, "mtx"))
     ad.settings.use_sparse_array_on_read = True
@@ -371,16 +372,14 @@ def test_read_array(
     ],
 )
 def test_dataset_append_disk(
-    tmp_path: Path,
+    diskfmt_store: Path | MemoryStore,
     sparse_format: type[CSMatrix],
     append_method: Callable[[list[CSMatrix]], CSMatrix],
-    diskfmt: Literal["h5ad", "zarr"],
 ):
-    path = tmp_path / f"test.{diskfmt.replace('ad', '')}"
     a = sparse_format(sparse.random(10, 10))
     b = sparse_format(sparse.random(10, 10))
 
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
     ad.io.write_elem(f, "a", a)
     ad.io.write_elem(f, "b", b)
     a_disk = sparse_dataset(subgroup(f, "a"))
@@ -398,18 +397,17 @@ def test_dataset_append_disk(
 @pytest.mark.parametrize("sparse_format", [sparse.csr_matrix, sparse.csc_matrix])
 @pytest.mark.parametrize("should_cache_indptr", [True, False])
 def test_lazy_array_cache(
-    tmp_path: Path,
     sparse_format: type[CSMatrix],
     zarr_metadata_key: Literal[".zarray", "zarr.json"],
     *,
     should_cache_indptr: bool,
 ):
     elems = {"indptr", "indices", "data"}
-    path = tmp_path / "test.zarr"
+    orig_store = MemoryStore()
     a = sparse_format(sparse.random(10, 10))
-    f = open_write_group(path, mode="a")
+    f = open_write_group(orig_store, mode="a")
     ad.io.write_elem(f, "X", a)
-    store = AccessTrackingStore(path, read_only=True)
+    store = AccessTrackingStore(orig_store)
     for elem in elems:
         store.initialize_key_trackers([f"X/{elem}"])
     f = zarr.open_group(store, mode="r")
@@ -509,7 +507,6 @@ def width_idx_kinds(
 )
 @pytest.mark.parametrize("read_data", [True, False], ids=["read", "no_read"])
 def test_data_access(
-    tmp_path: Path,
     sparse_format: type[CSMatrix],
     idx_maj: Idx,
     idx_min: Idx,
@@ -530,9 +527,9 @@ def test_data_access(
         )
         and not (open_func is sparse_dataset and not read_data)
     ]
-    path = tmp_path / "test.zarr"
+    orig_store = MemoryStore()
     a = sparse_format(np.eye(10, 10))
-    f = open_write_group(path, mode="a")
+    f = open_write_group(orig_store, mode="a")
     ad.io.write_elem(f, "X", a)
     data_arr = f["X/data"]
     assert isinstance(data_arr, zarr.Array)
@@ -541,11 +538,12 @@ def test_data_access(
     # chunk one at a time to count properly
     zarr.array(
         data,
-        store=path / "X" / "data",
+        store=orig_store,
+        path="X/data",
         chunks=(1,),
         zarr_format=f.metadata.zarr_format,
     )
-    store = AccessTrackingStore(path, read_only=True)
+    store = AccessTrackingStore(orig_store)
     store.initialize_key_trackers(["X/data"])
     f = zarr.open_group(store, mode="r")
     x_group = f["X"]
@@ -602,11 +600,10 @@ def test_wrong_shape(
         a_disk.append(b_disk)
 
 
-def test_reset_group(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]):
-    path = tmp_path / "test.zarr"
+def test_reset_group(diskfmt_store: Path | MemoryStore):
     base = sparse.random(100, 100, format="csr")
 
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
 
     ad.io.write_elem(f, "base", base)
     disk_mtx = sparse_dataset(subgroup(f, "base"))
@@ -653,25 +650,20 @@ def test_wrong_formats(tmp_path: Path):
     assert not np.any(diff.toarray())
 
 
-def test_anndata_sparse_compat(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]):
-    path = tmp_path / f"test.{diskfmt.replace('ad', '')}"
+def test_anndata_sparse_compat(diskfmt_store: Path | MemoryStore):
     base = sparse.random(100, 100, format="csr")
 
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
 
     ad.io.write_elem(f, "/", base)
     adata = ad.AnnData(sparse_dataset(subgroup(f, "/")))
     assert_equal(adata.X, base)
 
 
-def test_write(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]):
+def test_write(diskfmt_store: Path | MemoryStore):
     base = sparse.random(10, 10, format="csr")
 
-    f = (
-        open_write_group(tmp_path / f"parent_store.{diskfmt}", mode="a")
-        if diskfmt == "zarr"
-        else h5py.File(tmp_path / f"parent_store.{diskfmt}", "a")
-    )
+    f = open_store(diskfmt_store)
 
     ad.io.write_elem(f, "a_sparse_matrix", base)
     adata = ad.AnnData(sparse_dataset(subgroup(f, "a_sparse_matrix")))
diff --git a/tests/test_base.py b/tests/test_base.py
index dbb1a9f64..05121e94a 100644
--- a/tests/test_base.py
+++ b/tests/test_base.py
@@ -13,6 +13,7 @@
 from numpy import ma
 from scipy import sparse as sp
 from scipy.sparse import csr_matrix, issparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata import AnnData, ImplicitModificationWarning
@@ -61,22 +62,25 @@ def adata_on_disk(
     diskfmt: Literal["h5ad", "zarr"],
     adata: AnnData,
     tmp_path_factory: pytest.TempPathFactory,
-) -> Path:
-    path = (
+) -> tuple[Path | MemoryStore, bool]:
+    store = (
         tmp_path_factory.mktemp("disk_backed")
-        / f"{'sparse' if adata is adata_sparse else 'dense'}.{diskfmt}"
+        / f"{'sparse' if adata is adata_sparse else 'dense'}.h5ad"
+        if diskfmt == "h5ad"
+        else MemoryStore()
     )
-    getattr(adata, f"write_{diskfmt}")(path)
-    return path
+    getattr(adata, f"write_{diskfmt}")(store)
+    return store, adata is adata_sparse
 
 
 @pytest.mark.parametrize("elem_name", ["X", "obsm", "layers"])
 def test_cant_copy_disk_backed(
-    adata_on_disk: Path, elem_name: Literal["X", "obsm", "layers"]
+    adata_on_disk: tuple[Path | MemoryStore, bool],
+    elem_name: Literal["X", "obsm", "layers"],
 ):
-    is_sparse = "sparse" in str(adata_on_disk)
-    is_zarr = adata_on_disk.suffix == ".zarr"
-    root = (zarr.open if is_zarr else h5py.File)(adata_on_disk)
+    store, is_sparse = adata_on_disk
+    is_zarr = isinstance(store, MemoryStore)
+    root = (zarr.open if is_zarr else h5py.File)(store)
     assert isinstance(root, zarr.Group | h5py.File)
     elem = root["X"]
     X: object
@@ -907,9 +911,9 @@ def test_transpose_errors_with_backed_arrays(
     tmp_path: Path, storage: str, *, is_sparse: bool, in_x: bool
 ):
     adata = AnnData(X=csr_matrix(np.ones((3, 4))) if is_sparse else np.ones((3, 4)))
-    path = tmp_path / f"test.{storage}"
-    getattr(adata, f"write_{storage}")(path)
-    f = (h5py.File if storage == "h5ad" else zarr.open)(path)
+    store = tmp_path / "test.h5ad" if storage == "h5ad" else MemoryStore()
+    getattr(adata, f"write_{storage}")(store)
+    f = (h5py.File if storage == "h5ad" else zarr.open)(store)
     assert isinstance(f, zarr.Group | h5py.File)
     elem = f["X"]
     raw_array: object
diff --git a/tests/test_concatenate_disk.py b/tests/test_concatenate_disk.py
index e7edc081e..6bdf08726 100644
--- a/tests/test_concatenate_disk.py
+++ b/tests/test_concatenate_disk.py
@@ -10,6 +10,7 @@
 import pytest
 import zarr
 from scipy import sparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata import AnnData, concat
@@ -72,19 +73,29 @@ def max_loaded_elems(request) -> int:
     return request.param
 
 
-def _adatas_to_paths(
+def _make_store(
+    tmp_path: Path, file_format: str, name: str, *, on_disk_zarr: bool
+) -> Path | MemoryStore:
+    if file_format == "h5ad" or on_disk_zarr:
+        return tmp_path / f"{name}.{file_format}"
+    return MemoryStore()
+
+
+def _adatas_to_stores(
     adatas: Mapping[str, AnnData] | Collection[AnnData],
     tmp_path: Path,
     file_format: str,
-) -> dict[str, Path] | list[Path]:
-    """Gets list of adatas, writes them and returns their paths as zarr."""
-    paths: dict[str, Path] = {}
+    *,
+    on_disk_zarr: bool,
+) -> dict[str, Path | MemoryStore] | list[Path | MemoryStore]:
+    """Gets list of adatas, writes them and returns their stores."""
+    stores: dict[str, Path | MemoryStore] = {}
     for k, v in adatas.items() if isinstance(adatas, Mapping) else enumerate(adatas):
-        p = tmp_path / f"{k}.{file_format}"
-        with as_group(p, mode="a") as f:
+        store = _make_store(tmp_path, file_format, str(k), on_disk_zarr=on_disk_zarr)
+        with as_group(store, mode="a") as f:
             write_elem(f, "/", v)
-        paths[str(k)] = p
-    return paths if isinstance(adatas, Mapping) else list(paths.values())
+        stores[str(k)] = store
+    return stores if isinstance(adatas, Mapping) else list(stores.values())
 
 
 def assert_eq_concat_on_disk(
@@ -94,19 +105,23 @@ def assert_eq_concat_on_disk(
     max_loaded_elems: int | None = None,
     *args,
     merge_strategy: merge.StrategiesLiteral | None = None,
+    on_disk_zarr: bool = False,
     **kwargs,
-):
+) -> Path | MemoryStore:
+    """Concatenate on disk and compare to the in-memory result, returning the output store."""
     # create one from the concat function
     res1 = concat(adatas, *args, merge=merge_strategy, **kwargs)
     # create one from the on disk concat function
-    paths = _adatas_to_paths(adatas, tmp_path, file_format)
-    out_name = tmp_path / f"out.{file_format}"
+    stores = _adatas_to_stores(adatas, tmp_path, file_format, on_disk_zarr=on_disk_zarr)
     if max_loaded_elems is not None:
         kwargs["max_loaded_elems"] = max_loaded_elems
-    concat_on_disk(paths, out_name, *args, merge=merge_strategy, **kwargs)
-    with as_group(out_name, mode="r") as rg:
+
+    out = _make_store(tmp_path, file_format, "out", on_disk_zarr=on_disk_zarr)
+    concat_on_disk(stores, out, *args, merge=merge_strategy, **kwargs)
+    with as_group(out, mode="r") as rg:
         res2 = read_elem(rg)
     assert_equal(res1, res2, exact=False)
+    return out
 
 
 def get_array_type(array_type, axis):
@@ -257,15 +272,19 @@ def test_concatenate_xxxm(xxxm_adatas, tmp_path, file_format, join_type):
 
 
 def test_concatenate_zarr_stays_sharded_v3(xxxm_adatas, tmp_path):
-    assert_eq_concat_on_disk(xxxm_adatas, tmp_path, file_format="zarr")
-    g = zarr.open(tmp_path)
+    out = assert_eq_concat_on_disk(xxxm_adatas, tmp_path, file_format="zarr")
+    g = zarr.open(out)
     assert g.metadata.zarr_format == 3
 
     check_all_sharded(g)
 
 
 def test_singleton(xxxm_adatas, tmp_path, file_format):
-    assert_eq_concat_on_disk(xxxm_adatas[:1], tmp_path, file_format=file_format)
+    # A single input written to a path takes the `shutil` copy shortcut,
+    # so this test needs the file system.
+    assert_eq_concat_on_disk(
+        xxxm_adatas[:1], tmp_path, file_format=file_format, on_disk_zarr=True
+    )
 
 
 def test_output_dir_exists(tmp_path):
@@ -307,21 +326,22 @@ def test_no_open_h5_file_handles_after_error(tmp_path):
 
 
 def test_write_using_groups(tmp_path, file_format):
-    in_pth = tmp_path / f"in.{file_format}"
-    in_pth2 = tmp_path / f"in2.{file_format}"
-    out_pth = tmp_path / f"out.{file_format}"
+    in_store, in_store2, out_store = (
+        _make_store(tmp_path, file_format, name, on_disk_zarr=False)
+        for name in ["in", "in2", "out"]
+    )
 
     adata = AnnData(X=np.ones((2, 1)))
-    getattr(adata, f"write_{file_format}")(in_pth)
-    getattr(adata, f"write_{file_format}")(in_pth2)
+    getattr(adata, f"write_{file_format}")(in_store)
+    getattr(adata, f"write_{file_format}")(in_store2)
 
     with (
-        as_group(in_pth, mode="r") as f1,
-        as_group(in_pth2, mode="r") as f2,
-        as_group(out_pth, mode="w") as fout,
+        as_group(in_store, mode="r") as f1,
+        as_group(in_store2, mode="r") as f2,
+        as_group(out_store, mode="w") as fout,
     ):
         concat_on_disk([f1, f2], fout)
-    adata_out = getattr(ad, f"read_{file_format}")(out_pth)
+    adata_out = getattr(ad, f"read_{file_format}")(out_store)
     assert_equal(adata_out, concat([adata, adata]))
 
 
diff --git a/tests/test_dask.py b/tests/test_dask.py
index b0f4bbf7f..d7c232059 100644
--- a/tests/test_dask.py
+++ b/tests/test_dask.py
@@ -36,6 +36,7 @@
     from typing import Literal
 
     from numpy.typing import NDArray
+    from zarr.storage import MemoryStore
 
 
 pytest.importorskip("dask.array")
@@ -83,11 +84,10 @@ def test_dask_X_view():
     view.copy()
 
 
-def test_dask_write(adata, tmp_path, diskfmt):
+def test_dask_write(adata, diskfmt_store, diskfmt):
     import dask.array as da
     import numpy as np
 
-    pth = tmp_path / f"test_write.{diskfmt}"
     write = lambda x, y: getattr(x, f"write_{diskfmt}")(y)
     read = getattr(ad, f"read_{diskfmt}")
 
@@ -97,8 +97,8 @@ def test_dask_write(adata, tmp_path, diskfmt):
     adata.varm["a"] = da.random.random((N, 10))
 
     orig = adata
-    write(orig, pth)
-    curr = read(pth)
+    write(orig, diskfmt_store)
+    curr = read(diskfmt_store)
 
     with pytest.raises(AssertionError):
         assert_equal(curr.obsm["a"], curr.obsm["b"])
@@ -135,6 +135,8 @@ def test_dask_distributed_write(
     import numpy as np
 
     assert isinstance(adata.X, DaskArray)
+    # A real path, not an in-memory store: the dask workers are separate
+    # processes and have to see the same store as this one.
     pth = tmp_path / f"test_write.{diskfmt}"
     with as_group(pth, mode="w") as g, dd.Client(local_cluster_addr):
         M, N = adata.X.shape
@@ -166,11 +168,10 @@ def test_dask_distributed_write(
     assert isinstance(orig.varm["a"], DaskArray)
 
 
-def test_dask_to_memory_check_array_types(adata, tmp_path, diskfmt):
+def test_dask_to_memory_check_array_types(adata, diskfmt_store, diskfmt):
     import dask.array as da
     import numpy as np
 
-    pth = tmp_path / f"test_write.{diskfmt}"
     write = lambda x, y: getattr(x, f"write_{diskfmt}")(y)
     read = getattr(ad, f"read_{diskfmt}")
 
@@ -180,8 +181,8 @@ def test_dask_to_memory_check_array_types(adata, tmp_path, diskfmt):
     adata.varm["a"] = da.random.random((N, 10))
 
     orig = adata
-    write(orig, pth)
-    curr = read(pth)
+    write(orig, diskfmt_store)
+    curr = read(diskfmt_store)
 
     assert isinstance(orig.X, DaskArray)
     assert isinstance(orig.obsm["a"], DaskArray)
@@ -208,11 +209,10 @@ def test_dask_to_memory_check_array_types(adata, tmp_path, diskfmt):
     assert isinstance(orig.varm["a"], DaskArray)
 
 
-def test_dask_to_memory_copy_check_array_types(adata, tmp_path, diskfmt):
+def test_dask_to_memory_copy_check_array_types(adata, diskfmt_store, diskfmt):
     import dask.array as da
     import numpy as np
 
-    pth = tmp_path / f"test_write.{diskfmt}"
     write = lambda x, y: getattr(x, f"write_{diskfmt}")(y)
     read = getattr(ad, f"read_{diskfmt}")
 
@@ -222,8 +222,8 @@ def test_dask_to_memory_copy_check_array_types(adata, tmp_path, diskfmt):
     adata.varm["a"] = da.random.random((N, 10))
 
     orig = adata
-    write(orig, pth)
-    curr = read(pth)
+    write(orig, diskfmt_store)
+    curr = read(diskfmt_store)
 
     mem = orig.to_memory(copy=True)
 
@@ -337,7 +337,7 @@ def test_dask_to_memory_unbacked(array_func, mem_type):
 def test_dask_to_disk_view(
     to_dask: Callable[[NDArray], DaskArray],
     diskfmt: Literal["h5ad", "zarr"],
-    tmp_path: Path,
+    diskfmt_store: Path | MemoryStore,
 ) -> None:
     random_state = np.random.default_rng()
     arr = random_state.binomial(100, 0.005, (20, 15)).astype("float32")
@@ -345,9 +345,8 @@ def test_dask_to_disk_view(
     # TODO: need to change type for cupy
     orig = ad.AnnData(to_dask(arr))
     orig = orig[orig.shape[0] // 2]
-    path = tmp_path / f"test.{diskfmt}"
-    getattr(orig, f"write_{diskfmt}")(path)
-    roundtrip = getattr(ad.io, f"read_{diskfmt}")(path)
+    getattr(orig, f"write_{diskfmt}")(diskfmt_store)
+    roundtrip = getattr(ad.io, f"read_{diskfmt}")(diskfmt_store)
     assert_equal(roundtrip, orig)
 
 
diff --git a/tests/test_gpu.py b/tests/test_gpu.py
index 7b688896b..c5780589f 100644
--- a/tests/test_gpu.py
+++ b/tests/test_gpu.py
@@ -1,11 +1,10 @@
 from __future__ import annotations
 
-from typing import TYPE_CHECKING
-
 import numpy as np
 import pytest
 import zarr
 from scipy import sparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata import AnnData, Raw
@@ -14,9 +13,6 @@
 from anndata.compat import CSArray, CSMatrix, CupyCSRMatrix
 from anndata.tests.helpers import assert_equal
 
-if TYPE_CHECKING:
-    from pathlib import Path
-
 
 @pytest.mark.gpu
 def test_gpu():
@@ -72,12 +68,12 @@ def test_raw_gpu():
         slice(3, 10),
     ],
 )
-def test_get_with_zarr_gpu(tmp_path: Path, index: slice | np.ndarray):
+def test_get_with_zarr_gpu(index: slice | np.ndarray):
     adata = AnnData(X=sparse.random(50, 100, format="csr"))
-    zarr_path = tmp_path / "gpu_adata.zarr"
+    store = MemoryStore()
     # compressor None because there are no GPU compressors right now
-    ad.io.write_zarr(zarr_path, adata, compressor=None)
-    g = zarr.open_group(zarr_path, mode="r")
+    ad.io.write_zarr(store, adata, compressor=None)
+    g = zarr.open_group(store, mode="r")
     x_disk = g["X"]
     assert isinstance(x_disk, zarr.Group)
     adata = AnnData(X=sparse_dataset(x_disk))
diff --git a/tests/test_io_backwards_compat.py b/tests/test_io_backwards_compat.py
index 147d440d8..48fb8e92c 100644
--- a/tests/test_io_backwards_compat.py
+++ b/tests/test_io_backwards_compat.py
@@ -66,8 +66,7 @@ def test_no_diff(tmp_path: Path, archive_dir: Path) -> None:
     assert diff_proc.returncode == 0, diff_proc.stdout
 
 
-def test_clean_uns_backwards_compat(tmp_path, diskfmt):
-    pth = tmp_path / f"test_write.{diskfmt}"
+def test_clean_uns_backwards_compat(diskfmt_store, diskfmt):
     write = lambda x, y: getattr(x, f"write_{diskfmt}")(y)
     read = getattr(ad, f"read_{diskfmt}")
 
@@ -83,7 +82,7 @@ def test_clean_uns_backwards_compat(tmp_path, diskfmt):
         },
     )
 
-    write(orig, pth)
-    from_disk = read(pth)
+    write(orig, diskfmt_store)
+    from_disk = read(diskfmt_store)
 
     assert_equal(orig, from_disk)
diff --git a/tests/test_io_dispatched.py b/tests/test_io_dispatched.py
index 98b207d61..478432ec8 100644
--- a/tests/test_io_dispatched.py
+++ b/tests/test_io_dispatched.py
@@ -9,6 +9,7 @@
 import pytest
 import scipy.sparse as sp
 import zarr
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata._io.zarr import open_write_group
@@ -27,7 +28,7 @@
 
 
 @pytest.mark.zarr_io
-def test_read_dispatched_w_regex(tmp_path: Path):
+def test_read_dispatched_w_regex():
     def read_only_axis_dfs(func, elem_name: str, elem, iospec):
         if iospec.encoding_type == "anndata" or re.match(
             r"^/((obs)|(var))?(/.*)?$", elem_name
@@ -37,7 +38,7 @@ def read_only_axis_dfs(func, elem_name: str, elem, iospec):
             return None
 
     adata = gen_adata((1000, 100), **GEN_ADATA_NO_XARRAY_ARGS)
-    z = open_write_group(tmp_path)
+    z = open_write_group(MemoryStore())
 
     ad.io.write_elem(z, "/", adata)
     # TODO: see https://github.com/zarr-developers/zarr-python/issues/2716
@@ -53,7 +54,7 @@ def read_only_axis_dfs(func, elem_name: str, elem, iospec):
 
 
 @pytest.mark.zarr_io
-def test_read_dispatched_dask(tmp_path: Path):
+def test_read_dispatched_dask():
     import dask.array as da
 
     def read_as_dask_array(func, elem_name: str, elem, iospec):
@@ -71,7 +72,7 @@ def read_as_dask_array(func, elem_name: str, elem, iospec):
             return func(elem)
 
     adata = gen_adata((1000, 100), **GEN_ADATA_NO_XARRAY_ARGS)
-    z = open_write_group(tmp_path)
+    z = open_write_group(MemoryStore())
     ad.io.write_elem(z, "/", adata)
     # TODO: see https://github.com/zarr-developers/zarr-python/issues/2716
     if isinstance(z, zarr.Group):
@@ -91,9 +92,9 @@ def read_as_dask_array(func, elem_name: str, elem, iospec):
 
 
 @pytest.mark.zarr_io
-def test_read_dispatched_null_case(tmp_path: Path):
+def test_read_dispatched_null_case():
     adata = gen_adata((100, 100), **GEN_ADATA_NO_XARRAY_ARGS)
-    z = open_write_group(tmp_path)
+    z = open_write_group(MemoryStore())
     ad.io.write_elem(z, "/", adata)
     # TODO: see https://github.com/zarr-developers/zarr-python/issues/2716
     if isinstance(z, zarr.Group):
@@ -106,26 +107,23 @@ def test_read_dispatched_null_case(tmp_path: Path):
 
 @pytest.mark.zarr_io
 @pytest.mark.parametrize("sparse_format", ["csr", "csc"])
-def test_write_dispatched_csr_dataset(
-    tmp_path: Path, sparse_format: Literal["csr", "csc"]
-):
+def test_write_dispatched_csr_dataset(sparse_format: Literal["csr", "csc"]):
+    store = MemoryStore()
     ad.io.write_elem(
-        open_write_group(tmp_path / "arr.zarr"),
+        open_write_group(store),
         "/",
         sp.random(10, 10, format=sparse_format),
     )
-    X = ad.io.sparse_dataset(zarr.open_group(tmp_path / "arr.zarr"))
+    X = ad.io.sparse_dataset(zarr.open_group(store))
 
     def zarr_writer(func, store, elem_name: str, elem, iospec, dataset_kwargs):
         assert iospec.encoding_type == f"{sparse_format}_matrix"
 
-    write_dispatched(
-        zarr.open_group(tmp_path / "check.zarr", mode="w"), "/X", X, zarr_writer
-    )
+    write_dispatched(zarr.open_group(MemoryStore(), mode="w"), "/X", X, zarr_writer)
 
 
 @pytest.mark.zarr_io
-def test_write_dispatched_chunks(tmp_path: Path):
+def test_write_dispatched_chunks():
     from itertools import chain, repeat
 
     def determine_chunks(elem_shape, specified_chunks):
@@ -172,7 +170,7 @@ def set_copy(d, **kwargs):
         else:
             func(store, k, elem, dataset_kwargs=dataset_kwargs)
 
-    z = open_write_group(tmp_path)
+    z = open_write_group(MemoryStore())
 
     write_dispatched(z, "/", adata, callback=write_chunked)
 
@@ -199,7 +197,6 @@ def test_io_dispatched_keys(tmp_path: Path):
     zarr_read_keys: list[str] = []
 
     h5ad_path = tmp_path / "test.h5ad"
-    zarr_path = tmp_path / "test.zarr"
 
     def writer(func, store, k, elem, dataset_kwargs, iospec, keys):
         keys.append(f"{store.name}/{k}")
@@ -215,7 +212,7 @@ def reader(func, elem_name: str, elem, iospec, keys):
         write_dispatched(f, "/", adata, callback=partial(writer, keys=h5ad_write_keys))
         _ = read_dispatched(f, partial(reader, keys=h5ad_read_keys))
 
-    f = open_write_group(zarr_path)
+    f = open_write_group(MemoryStore())
     write_dispatched(f, "/", adata, callback=partial(writer, keys=zarr_write_keys))
     _ = read_dispatched(f, partial(reader, keys=zarr_read_keys))
 
diff --git a/tests/test_io_elementwise.py b/tests/test_io_elementwise.py
index 125c9526c..22fc9de00 100644
--- a/tests/test_io_elementwise.py
+++ b/tests/test_io_elementwise.py
@@ -17,6 +17,7 @@
 import zarr
 from packaging.version import Version
 from scipy import sparse
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata._io.specs import _REGISTRY, IOSpec, get_spec
@@ -33,6 +34,7 @@
     assert_equal,
     check_all_sharded,
     gen_adata,
+    open_store,
     visititems_zarr,
 )
 
@@ -62,7 +64,7 @@ def store(
         file = h5py.File(tmp_path / "test.h5ad", "w")
         store = cast("h5py.Group", file["/"])
     elif diskfmt == "zarr":
-        store = open_write_group(tmp_path / "test.zarr")
+        store = open_write_group(MemoryStore())
     else:
         pytest.fail(f"Unknown store type: {diskfmt}")
 
@@ -773,12 +775,12 @@ def test_write_to_root(store: _GroupStorageType, value):
     "consolidated", [True, False], ids=["consolidated", "unconsolidated"]
 )
 @pytest.mark.zarr_io
-def test_read_zarr_from_group(tmp_path, consolidated):
+def test_read_zarr_from_group(consolidated):
     # https://github.com/scverse/anndata/issues/1056
-    pth = tmp_path / "test.zarr"
+    store = MemoryStore()
     adata = gen_adata((3, 2), **GEN_ADATA_NO_XARRAY_ARGS)
 
-    z = open_write_group(pth)
+    z = open_write_group(store)
     write_elem(z.create_group("table"), "table", adata)
 
     if consolidated:
@@ -793,7 +795,7 @@ def test_read_zarr_from_group(tmp_path, consolidated):
 
     read_func = zarr.open_consolidated if consolidated else zarr.open
 
-    z = read_func(pth)
+    z = read_func(store)
     expected = ad.read_zarr(z["table/table"])
     assert_equal(adata, expected)
 
@@ -853,13 +855,11 @@ def test_io_pd_cow(
 
 
 def test_read_sparse_array(
-    tmp_path: Path,
+    diskfmt_store: Path | MemoryStore,
     sparse_format: Literal["csr", "csc"],
-    diskfmt: Literal["h5ad", "zarr"],
 ):
-    path = tmp_path / f"test.{diskfmt.replace('ad', '')}"
     a = sparse.random(100, 100, format=sparse_format)
-    f = open_write_group(path, mode="a") if diskfmt == "zarr" else h5py.File(path, "a")
+    f = open_store(diskfmt_store)
     ad.io.write_elem(f, "mtx", a)
     ad.settings.use_sparse_array_on_read = True
     mtx = ad.io.read_elem(f["mtx"])
@@ -939,13 +939,13 @@ def test_h5_unchunked(
 
 
 @pytest.mark.zarr_io
-def test_write_auto_sharded(tmp_path: Path):
-    path = tmp_path / "check.zarr"
+def test_write_auto_sharded():
+    store = MemoryStore()
     adata = gen_adata((100, 10), **GEN_ADATA_NO_XARRAY_ARGS)
     with ad.settings.override(auto_shard_zarr_v3=True, zarr_write_format=3):
-        adata.write_zarr(path)
+        adata.write_zarr(store)
 
-    check_all_sharded(zarr.open_group(path))
+    check_all_sharded(zarr.open_group(store))
 
 
 @pytest.mark.zarr_io
@@ -953,9 +953,8 @@ def test_write_auto_sharded(tmp_path: Path):
     Version(version("zarr")) < Version("3.1.4"),
     reason="autosharding with chosen size was not available",
 )
-def test_write_auto_sharded_size(tmp_path: Path):
-    path = tmp_path / "check_shards.zarr"
-    z = zarr.open_group(path)
+def test_write_auto_sharded_size():
+    z = zarr.open_group(MemoryStore())
     ad.io.write_elem(z, "two_shards", np.arange(101), dataset_kwargs={"chunks": (7,)})
     two_shards = z["two_shards"]
     assert isinstance(two_shards, zarr.Array)
@@ -966,12 +965,12 @@ def test_write_auto_sharded_size(tmp_path: Path):
 
 
 @pytest.mark.zarr_io
-def test_write_shards_by_default(tmp_path: Path):
-    path = tmp_path / "check.zarr"
+def test_write_shards_by_default():
+    store = MemoryStore()
     adata = gen_adata((100, 10), **GEN_ADATA_NO_XARRAY_ARGS)
     ad.settings.reset("auto_shard_zarr_v3")
-    adata.write_zarr(path)
-    check_all_sharded(zarr.open_group(path))
+    adata.write_zarr(store)
+    check_all_sharded(zarr.open_group(store))
 
 
 @pytest.mark.zarr_io
@@ -979,9 +978,8 @@ def test_write_shards_by_default(tmp_path: Path):
     Version(version("zarr")) < Version("3.1.4"),
     reason="autosharding with chosen size was not available",
 )
-def test_write_auto_sharded_size_sparse(tmp_path: Path):
-    path = "memory://check_shards.zarr"
-    z = zarr.open_group(path)
+def test_write_auto_sharded_size_sparse():
+    z = zarr.open_group(MemoryStore())
     mat = sparse.random(
         1000, 1000, density=0.5, format="csr", random_state=np.random.default_rng(42)
     )
@@ -998,8 +996,8 @@ def test_write_auto_sharded_size_sparse(tmp_path: Path):
 
 
 @pytest.mark.zarr_io
-def test_write_auto_sharded_does_not_override(tmp_path: Path):
-    z = open_write_group(tmp_path / "arr.zarr", zarr_format=3)
+def test_write_auto_sharded_does_not_override():
+    z = open_write_group(MemoryStore(), zarr_format=3)
     X = sparse.random(
         100, 100, density=0.1, format="csr", random_state=np.random.default_rng(42)
     )
diff --git a/tests/test_io_partial.py b/tests/test_io_partial.py
index 9abef5cb8..2587ba8cb 100644
--- a/tests/test_io_partial.py
+++ b/tests/test_io_partial.py
@@ -2,47 +2,41 @@
 
 import warnings
 from importlib.util import find_spec
-from pathlib import Path
 
-import h5py
 import numpy as np
 import pytest
-import zarr
 from scipy.sparse import csr_matrix
 
 from anndata import AnnData, settings
 from anndata._io.specs.registry import read_elem_partial
 from anndata.io import read_elem, write_h5ad, write_zarr
+from anndata.tests.helpers import open_store
 
 X = np.array([[1.0, 0.0, 3.0], [4.0, 0.0, 6.0], [0.0, 8.0, 0.0]], dtype="float32")
 X_check = np.array([[4.0, 0.0], [0.0, 8.0]], dtype="float32")
 
 WRITER = dict(h5ad=write_h5ad, zarr=write_zarr)
-READER = dict(h5ad=h5py.File, zarr=zarr.open)
 
 
 @pytest.mark.parametrize("typ", [np.asarray, csr_matrix])
-def test_read_partial_X(tmp_path, typ, diskfmt):
+def test_read_partial_X(diskfmt_store, typ, diskfmt):
     adata = AnnData(X=typ(X))
 
-    path = Path(tmp_path) / ("test_tp_X." + diskfmt)
+    WRITER[diskfmt](diskfmt_store, adata)
 
-    WRITER[diskfmt](path, adata)
-
-    store = READER[diskfmt](path, mode="r")
+    store = open_store(diskfmt_store, "r")
     if diskfmt == "zarr":
         X_part = read_elem_partial(store["X"], indices=([1, 2], [0, 1]))
     else:
         # h5py doesn't allow fancy indexing across multiple dimensions
         X_part = read_elem_partial(store["X"], indices=([1, 2],))
         X_part = X_part[:, [0, 1]]
-        store.close()
 
     assert np.all(X_check == X_part)
 
 
 @pytest.mark.skipif(not find_spec("scanpy"), reason="Scanpy is not installed")
-def test_read_partial_adata(tmp_path, diskfmt):
+def test_read_partial_adata(diskfmt_store, diskfmt):
     import scanpy as sc
 
     with warnings.catch_warnings():
@@ -51,14 +45,12 @@ def test_read_partial_adata(tmp_path, diskfmt):
         )
         adata = sc.datasets.pbmc68k_reduced()
 
-    path = Path(tmp_path) / ("test_rp." + diskfmt)
-
     # we’re not adding things to read_partial anymore, so it can only read non-nullable strings.
     # therefore force writing old format here
     with settings.override(allow_write_nullable_strings=False):
-        WRITER[diskfmt](path, adata)
+        WRITER[diskfmt](diskfmt_store, adata)
 
-    storage = READER[diskfmt](path, mode="r")
+    storage = open_store(diskfmt_store, "r")
 
     obs_idx = [1, 2]
     var_idx = [0, 3]
diff --git a/tests/test_io_utils.py b/tests/test_io_utils.py
index cec33ec75..eec712382 100644
--- a/tests/test_io_utils.py
+++ b/tests/test_io_utils.py
@@ -63,9 +63,8 @@ def read_attr(_):
             read_attr(group["group"])
 
 
-def test_write_error_info(diskfmt, tmp_path):
-    pth = tmp_path / f"failed_write.{diskfmt}"
-    write = lambda x: getattr(x, f"write_{diskfmt}")(pth)
+def test_write_error_info(diskfmt, diskfmt_store):
+    write = lambda x: getattr(x, f"write_{diskfmt}")(diskfmt_store)
 
     # Assuming we don't define a writer for tuples
     a = ad.AnnData(uns={"a": {"b": {"c": (1, 2, 3)}}})
diff --git a/tests/test_readwrite.py b/tests/test_readwrite.py
index 831de28b1..dd3ac7d4a 100644
--- a/tests/test_readwrite.py
+++ b/tests/test_readwrite.py
@@ -3,7 +3,7 @@
 import re
 import warnings
 import zipfile
-from contextlib import contextmanager, nullcontext
+from contextlib import contextmanager
 from functools import partial
 from importlib.util import find_spec
 from pathlib import Path
@@ -16,6 +16,7 @@
 import pytest
 import zarr
 from scipy.sparse import csc_array, csc_matrix, csr_array, csr_matrix
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata._io.specs.registry import IORegistryError
@@ -30,6 +31,7 @@
     gen_adata,
     jnp,
     jnp_array_or_idempotent,
+    open_store,
 )
 from anndata.utils import get_literal_members
 
@@ -39,6 +41,8 @@
 
     from zarr.storage import StoreLike
 
+    from anndata._types import _GroupStorageType
+
 HERE = Path(__file__).parent
 ARRAY_TYPES = [
     pytest.param(np.array, id="np.array"),
@@ -105,15 +109,6 @@ def rw(backing_h5ad) -> tuple[ad.AnnData, ad.AnnData]:
     return curr, orig
 
 
-@contextmanager
-def open_store(
-    path: Path, diskfmt: Literal["h5ad", "zarr"]
-) -> Generator[h5py.File | zarr.Group, None, None]:
-    f = zarr.open_group(path) if diskfmt == "zarr" else h5py.File(path, "r")
-    with f if isinstance(f, h5py.File) else nullcontext():
-        yield f
-
-
 @pytest.fixture(params=[np.uint8, np.int32, np.int64, np.float32, np.float64])
 def dtype(request):
     return request.param
@@ -194,13 +189,11 @@ def _set_non_2d(
 
 
 @pytest.mark.parametrize("typ", ARRAY_TYPES)
-def test_readwrite_roundtrip(typ, tmp_path, diskfmt, diskfmt2):
-    pth1 = tmp_path / f"first.{diskfmt}"
-    write1 = lambda x: getattr(x, f"write_{diskfmt}")(pth1)
-    read1 = lambda: getattr(ad, f"read_{diskfmt}")(pth1)
-    pth2 = tmp_path / f"second.{diskfmt2}"
-    write2 = lambda x: getattr(x, f"write_{diskfmt2}")(pth2)
-    read2 = lambda: getattr(ad, f"read_{diskfmt2}")(pth2)
+def test_readwrite_roundtrip(typ, diskfmt, diskfmt2, diskfmt_store, diskfmt2_store):
+    write1 = lambda x: getattr(x, f"write_{diskfmt}")(diskfmt_store)
+    read1 = lambda: getattr(ad, f"read_{diskfmt}")(diskfmt_store)
+    write2 = lambda x: getattr(x, f"write_{diskfmt2}")(diskfmt2_store)
+    read2 = lambda: getattr(ad, f"read_{diskfmt2}")(diskfmt2_store)
 
     adata1 = ad.AnnData(typ(X_list), obs=obs_dict, var=var_dict, uns=uns_dict)
     write1(adata1)
@@ -214,17 +207,17 @@ def test_readwrite_roundtrip(typ, tmp_path, diskfmt, diskfmt2):
 
 
 @pytest.mark.zarr_io
-def test_readwrite_roundtrip_async(tmp_path):
+def test_readwrite_roundtrip_async():
     import asyncio
 
     async def _do_test():
-        zarr_path = tmp_path / "first.zarr"
+        store = MemoryStore()
 
         adata1 = ad.AnnData(
             csr_matrix(X_list), obs=obs_dict, var=var_dict, uns=uns_dict
         )
-        adata1.write_zarr(zarr_path)
-        adata2 = ad.read_zarr(zarr_path)
+        adata1.write_zarr(store)
+        adata2 = ad.read_zarr(store)
 
         assert_equal(adata2, adata1)
 
@@ -252,8 +245,9 @@ def test_readwrite_kitchensink(
         adata_mid.write(tmp_path / "mid.h5ad", **dataset_kwargs)
         adata = ad.read_h5ad(tmp_path / "mid.h5ad")
     else:
-        adata_src.write_zarr(tmp_path / "test_zarr_dir")
-        adata = ad.read_zarr(tmp_path / "test_zarr_dir")
+        store = MemoryStore()
+        adata_src.write_zarr(store)
+        adata = ad.read_zarr(store)
     assert isinstance(adata.obs["oanno1"].dtype, pd.CategoricalDtype)
     assert not isinstance(adata.obs["oanno2"].dtype, pd.CategoricalDtype)
     assert adata.obs.index.tolist() == ["name1", "name2", "name3"]
@@ -371,46 +365,42 @@ def test_readwrite_backed(typ, backing_h5ad: Path) -> None:
 )
 def test_readwrite_equivalent_h5ad_zarr(tmp_path: Path, typ) -> None:
     h5ad_pth = tmp_path / "adata.h5ad"
-    zarr_pth = tmp_path / "adata.zarr"
 
     M, N = 100, 101
     adata = gen_adata((M, N), X_type=typ, **GEN_ADATA_NO_XARRAY_ARGS)
     assert not adata.unwriteable()
 
     adata.raw = adata.copy()
-
+    store_mem = MemoryStore()
+    store_disk = tmp_path / "adata.zarr"
     adata.write_h5ad(h5ad_pth)
-    adata.write_zarr(zarr_pth)
+    adata.write_zarr(store_mem)
+    adata.write_zarr(store_disk)
     from_h5ad = ad.read_h5ad(h5ad_pth)
-    from_zarr = ad.read_zarr(zarr_pth)
+    from_zarr_mem = ad.read_zarr(store_mem)
+    from_zarr_disk = ad.read_zarr(store_disk)
 
-    assert_equal(from_h5ad, from_zarr, exact=True)
+    assert_equal(from_h5ad, from_zarr_mem, exact=True)
+    assert_equal(from_h5ad, from_zarr_disk, exact=True)
 
 
 @contextmanager
-def store_context(path: Path):
-    if path.suffix == ".zarr":
-        store = open_write_group(path, mode="r+")
-    else:
-        file = h5py.File(path, "r+")
-        store = file["/"]
-    yield store
-    if "file" in locals():
-        file.close()
-
-
-@pytest.mark.parametrize(
-    ("name", "read", "write"),
-    [
-        ("adata.h5ad", ad.read_h5ad, ad.AnnData.write_h5ad),
-        ("adata.zarr", ad.read_zarr, ad.AnnData.write_zarr),
-    ],
-)
-def test_read_full_io_error(tmp_path, name, read, write):
+def store_context(store: Path | MemoryStore) -> Generator[_GroupStorageType]:
+    if isinstance(store, MemoryStore):
+        yield open_write_group(store, mode="r+")
+        return
+    with h5py.File(store, "r+") as file:
+        yield file["/"]
+
+
+# Not the `diskfmt` fixture: the consolidated-metadata canary below only
+# applies to zarr v3, and which zarr format is written is beside the point here.
+@pytest.mark.parametrize("store_type", ["h5ad", "zarr"])
+def test_read_full_io_error(tmp_path: Path, store_type: Literal["h5ad", "zarr"]):
+    store_loc = tmp_path / "adata.h5ad" if store_type == "h5ad" else MemoryStore()
     adata = gen_adata((4, 3), **GEN_ADATA_NO_XARRAY_ARGS)
-    path = tmp_path / name
-    write(adata, path)
-    with store_context(path) as store:
+    getattr(adata, f"write_{store_type}")(store_loc)
+    with store_context(store_loc) as store:
         if isinstance(store, zarr.Group):
             # see https://github.com/zarr-developers/zarr-python/issues/2716 for the issue
             # with re-opening without syncing attributes explicitly
@@ -435,7 +425,7 @@ def test_read_full_io_error(tmp_path, name, read, write):
         IORegistryError,
         match=r"raised while reading key 'obs'.*from /$",
     ) as exc_info:
-        read(path)
+        getattr(ad, f"read_{store_type}")(store_loc)
     assert re.search(
         r"No read method registered for IOSpec\(encoding_type='invalid', encoding_version='0.2.0'\)",
         str(exc_info.value),
@@ -491,11 +481,9 @@ def check_compressed(key, value):
 @pytest.mark.parametrize(
     "use_compression", [True, False], ids=["compressed", "uncompressed"]
 )
-def test_zarr_compression(
-    tmp_path: Path, zarr_write_format: Literal[2, 3], *, use_compression: bool
-):
+def test_zarr_compression(zarr_write_format: Literal[2, 3], *, use_compression: bool):
     ad.settings.zarr_write_format = zarr_write_format
-    pth = str(Path(tmp_path) / "adata.zarr")
+    store = MemoryStore()
     adata = gen_adata((10, 8), **GEN_ADATA_NO_XARRAY_ARGS)
     if not use_compression:
         compressor = None
@@ -511,7 +499,7 @@ def test_zarr_compression(
         compressor = ZstdCodec(level=3, checksum=True)
     wrongly_compressed = []
 
-    ad.io.write_zarr(pth, adata, compressor=compressor)
+    ad.io.write_zarr(store, adata, compressor=compressor)
 
     def check_compressed(value, key):
         if not isinstance(value, zarr.Array) or value.shape == ():
@@ -527,18 +515,16 @@ def check_compressed(value, key):
         ):
             wrongly_compressed.append(key)
 
-    f = zarr.open_group(pth, mode="r")
+    f = zarr.open_group(store, mode="r")
     for key, value in f.members(max_depth=None):
         check_compressed(value, key)
     assert not wrongly_compressed, "Some elements were not (un)compressed correctly"
 
-    expected = ad.read_zarr(pth)
+    expected = ad.read_zarr(store)
     assert_equal(adata, expected)
 
 
-def test_changed_obs_var_names(tmp_path, diskfmt):
-    filepth = tmp_path / f"test.{diskfmt}"
-
+def test_changed_obs_var_names(diskfmt, diskfmt_store):
     orig = gen_adata((10, 10), **GEN_ADATA_NO_XARRAY_ARGS)
     orig.obs_names = orig.obs_names.rename("obs")
     orig.var_names = orig.var_names.rename("var")
@@ -546,8 +532,8 @@ def test_changed_obs_var_names(tmp_path, diskfmt):
     modified.obs_names = modified.obs_names.rename("cells")
     modified.var_names = modified.var_names.rename("genes")
 
-    getattr(orig, f"write_{diskfmt}")(filepth)
-    read = getattr(ad, f"read_{diskfmt}")(filepth)
+    getattr(orig, f"write_{diskfmt}")(diskfmt_store)
+    read = getattr(ad, f"read_{diskfmt}")(diskfmt_store)
 
     assert_equal(orig, read, exact=True)
     assert orig.var.index.name == "var"
@@ -637,21 +623,14 @@ def hash_dir_contents(dir: Path) -> dict[str, bytes]:
     assert hash_dir_contents(view_pth) == hash_dir_contents(copy_pth)
 
 
-@pytest.mark.parametrize(
-    ("read", "write", "name"),
-    [
-        pytest.param(ad.read_h5ad, ad.io.write_h5ad, "test_empty.h5ad"),
-        pytest.param(ad.read_zarr, ad.io.write_zarr, "test_empty.zarr"),
-    ],
-)
 @pytest.mark.parametrize(
     "xp_array",
     [np.array, pytest.param(jnp_array_or_idempotent, marks=pytest.mark.array_api)],
 )
-def test_readwrite_empty(read, write, name: str, tmp_path: Path, xp_array) -> None:
+def test_readwrite_empty(diskfmt, diskfmt_store, xp_array) -> None:
     adata = ad.AnnData(uns=dict(empty=xp_array([]).astype(float)))
-    write(tmp_path / name, adata)
-    ad_read = read(tmp_path / name)
+    getattr(ad.io, f"write_{diskfmt}")(diskfmt_store, adata)
+    ad_read = getattr(ad, f"read_{diskfmt}")(diskfmt_store)
     assert ad_read.uns["empty"] is not None
     assert ad_read.uns["empty"].shape == (0,)
 
@@ -678,9 +657,11 @@ def test_read_umi_tools():
 
 @pytest.mark.parametrize("s2c", [True, False], ids=["str2cat", "preserve"])
 def test_write_categorical(
-    *, tmp_path: Path, diskfmt: Literal["h5ad", "zarr"], s2c: bool
+    *,
+    diskfmt: Literal["h5ad", "zarr"],
+    diskfmt_store: Path | MemoryStore,
+    s2c: bool,
 ) -> None:
-    adata_pth = tmp_path / f"adata.{diskfmt}"
     obs = dict(
         str=pd.array(["a", "a", "b", pd.NA, pd.NA], dtype="string"),
         cat=pd.Categorical(["a", "a", "b", np.nan, np.nan]),
@@ -689,9 +670,9 @@ def test_write_categorical(
     orig = ad.AnnData(obs=pd.DataFrame(obs))
     with ad.settings.override(allow_write_nullable_strings=True):
         getattr(orig, f"write_{diskfmt}")(
-            adata_pth, convert_strings_to_categoricals=s2c
+            diskfmt_store, convert_strings_to_categoricals=s2c
         )
-    curr: ad.AnnData = getattr(ad, f"read_{diskfmt}")(adata_pth)
+    curr: ad.AnnData = getattr(ad, f"read_{diskfmt}")(diskfmt_store)
     assert isinstance(orig.obs, pd.DataFrame)
     assert isinstance(curr.obs, pd.DataFrame)
     assert np.all(orig.obs.notna() == curr.obs.notna())
@@ -700,13 +681,12 @@ def test_write_categorical(
     assert curr.obs["cat"].dtype == "category"
 
 
-def test_write_categorical_index(tmp_path, diskfmt):
-    adata_pth = tmp_path / f"adata.{diskfmt}"
+def test_write_categorical_index(diskfmt, diskfmt_store):
     orig = ad.AnnData(
         uns={"df": pd.DataFrame({}, index=pd.Categorical(list("aabcd")))},
     )
-    getattr(orig, f"write_{diskfmt}")(adata_pth)
-    curr = getattr(ad, f"read_{diskfmt}")(adata_pth)
+    getattr(orig, f"write_{diskfmt}")(diskfmt_store)
+    curr = getattr(ad, f"read_{diskfmt}")(diskfmt_store)
     # Also covered by next assertion, but checking this value specifically
     pd.testing.assert_index_equal(
         orig.uns["df"].index, curr.uns["df"].index, exact=True
@@ -716,8 +696,7 @@ def test_write_categorical_index(tmp_path, diskfmt):
 
 @pytest.mark.parametrize("colname", ["_index"])
 @pytest.mark.parametrize("attr", ["obs", "varm_df"])
-def test_dataframe_reserved_columns(tmp_path, diskfmt, colname, attr):
-    adata_pth = tmp_path / f"adata.{diskfmt}"
+def test_dataframe_reserved_columns(diskfmt, diskfmt_store, colname, attr):
     orig = ad.AnnData(
         obs=pd.DataFrame(index=np.arange(5)), var=pd.DataFrame(index=np.arange(5))
     )
@@ -732,10 +711,10 @@ def test_dataframe_reserved_columns(tmp_path, diskfmt, colname, attr):
     else:
         pytest.fail(f"Unexpected attr: {attr}")
     with pytest.raises(ValueError, match=rf"{colname}.*reserved name"):
-        getattr(to_write, f"write_{diskfmt}")(adata_pth)
+        getattr(to_write, f"write_{diskfmt}")(diskfmt_store)
 
 
-def test_write_large_categorical(tmp_path, diskfmt):
+def test_write_large_categorical(diskfmt, diskfmt_store):
     M = 30_000
     N = 1000
     ls = np.array(list(ascii_letters))
@@ -750,7 +729,6 @@ def random_cats(n):
         return cats
 
     cats = np.array(sorted(random_cats(10_000)))
-    adata_pth = tmp_path / f"adata.{diskfmt}"
     n_cats = len(np.unique(cats))
     orig = ad.AnnData(
         csr_matrix(([1], ([0], [0])), shape=(M, N)),
@@ -759,18 +737,18 @@ def random_cats(n):
             cat2=pd.Categorical.from_codes(np.random.choice(n_cats, M), cats),
         ),
     )
-    getattr(orig, f"write_{diskfmt}")(adata_pth)
-    curr = getattr(ad, f"read_{diskfmt}")(adata_pth)
+    getattr(orig, f"write_{diskfmt}")(diskfmt_store)
+    curr = getattr(ad, f"read_{diskfmt}")(diskfmt_store)
     assert_equal(orig, curr)
 
 
-def test_write_string_type_error(tmp_path, diskfmt):
+def test_write_string_type_error(diskfmt, diskfmt_store):
     adata = ad.AnnData(obs=dict(obs_names=list("abc")))
     adata.obs[b"c"] = np.zeros(3)
 
     # This should error, and tell you which key is at fault
     with pytest.raises(TypeError, match=r"writing key 'obs'") as exc_info:
-        getattr(adata, f"write_{diskfmt}")(tmp_path / f"adata.{diskfmt}")
+        getattr(adata, f"write_{diskfmt}")(diskfmt_store)
 
     assert "b'c'" in str(exc_info.value)
 
@@ -795,27 +773,26 @@ def test_hdf5_attribute_conversion(tmp_path, teststring, encoding, length):
 
 
 @pytest.mark.zarr_io
-def test_zarr_chunk_X(tmp_path):
-    zarr_pth = Path(tmp_path) / "test.zarr"
+def test_zarr_chunk_X():
+    store = MemoryStore()
     adata = gen_adata((100, 100), X_type=np.array, **GEN_ADATA_NO_XARRAY_ARGS)
-    adata.write_zarr(zarr_pth, chunks=(10, 10))
+    adata.write_zarr(store, chunks=(10, 10))
 
-    z = zarr.open(zarr_pth)
+    z = zarr.open(store)
     assert z["X"].chunks == (10, 10)
-    from_zarr = ad.read_zarr(zarr_pth)
+    from_zarr = ad.read_zarr(store)
     assert_equal(from_zarr, adata)
 
 
-def test_write_x_none(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]) -> None:
+def test_write_x_none(
+    diskfmt: Literal["h5ad", "zarr"], diskfmt_store: Path | MemoryStore
+) -> None:
     adata = ad.AnnData(shape=(10, 10), obs={"a": np.ones(10)}, var={"b": np.ones(10)})
-    p = tmp_path / f"adata.{diskfmt}"
     write = getattr(adata, f"write_{diskfmt}")
 
-    write(p)
-    with open_store(p, diskfmt) as f:
-        root_keys = list(f.keys())
+    write(diskfmt_store)
 
-    assert "X" not in root_keys
+    assert "X" not in open_store(diskfmt_store, "r")
 
 
 ################################
@@ -824,16 +801,16 @@ def test_write_x_none(tmp_path: Path, diskfmt: Literal["h5ad", "zarr"]) -> None:
 
 
 def _do_roundtrip(
-    adata: ad.AnnData, pth: Path, diskfmt: Literal["h5ad", "zarr"]
+    adata: ad.AnnData, store: Path | MemoryStore, diskfmt: Literal["h5ad", "zarr"]
 ) -> ad.AnnData:
-    getattr(adata, f"write_{diskfmt}")(pth)
-    return getattr(ad, f"read_{diskfmt}")(pth)
+    getattr(adata, f"write_{diskfmt}")(store)
+    return getattr(ad, f"read_{diskfmt}")(store)
 
 
 @pytest.fixture
 def roundtrip(
     diskfmt: Literal["h5ad", "zarr"],
-) -> Callable[[ad.AnnData, Path], ad.AnnData]:
+) -> Callable[[ad.AnnData, Path | MemoryStore], ad.AnnData]:
     return partial(_do_roundtrip, diskfmt=diskfmt)
 
 
@@ -842,10 +819,8 @@ def roundtrip2(diskfmt2):
     return partial(_do_roundtrip, diskfmt=diskfmt2)
 
 
-def test_write_string_types(tmp_path, diskfmt, roundtrip):
+def test_write_string_types(diskfmt_store, roundtrip):
     # https://github.com/scverse/anndata/issues/456
-    adata_pth = tmp_path / f"adata.{diskfmt}"
-
     adata = ad.AnnData(
         obs=pd.DataFrame(
             np.ones((3, 2)),
@@ -854,13 +829,13 @@ def test_write_string_types(tmp_path, diskfmt, roundtrip):
         ),
     )
 
-    from_disk = roundtrip(adata, adata_pth)
+    from_disk = roundtrip(adata, diskfmt_store)
 
     assert_equal(adata, from_disk)
 
 
 @pytest.mark.skipif(not find_spec("scanpy"), reason="Scanpy is not installed")
-def test_scanpy_pbmc68k(tmp_path, diskfmt, roundtrip, diskfmt2, roundtrip2):
+def test_scanpy_pbmc68k(roundtrip, roundtrip2, diskfmt_store, diskfmt2_store):
     import scanpy as sc
 
     # TODO: remove filters (here and elsewhere) once https://github.com/scverse/scanpy/issues/3879 is fixed
@@ -872,9 +847,9 @@ def test_scanpy_pbmc68k(tmp_path, diskfmt, roundtrip, diskfmt2, roundtrip2):
         pbmc = sc.datasets.pbmc68k_reduced()
 
     # Do we read okay
-    from_disk1 = roundtrip(pbmc, tmp_path / f"test1.{diskfmt}")
+    from_disk1 = roundtrip(pbmc, diskfmt_store)
     # Can we round trip
-    from_disk2 = roundtrip2(from_disk1, tmp_path / f"test2.{diskfmt2}")
+    from_disk2 = roundtrip2(from_disk1, diskfmt2_store)
 
     assert_equal(pbmc, from_disk1)  # Not expected to be exact due to `nan`s
     assert_equal(pbmc, from_disk2)
@@ -883,9 +858,8 @@ def test_scanpy_pbmc68k(tmp_path, diskfmt, roundtrip, diskfmt2, roundtrip2):
 @pytest.mark.filterwarnings(r"ignore:Observation names are not unique:UserWarning")
 @pytest.mark.skipif(not find_spec("scanpy"), reason="Scanpy is not installed")
 def test_scanpy_krumsiek11(
-    tmp_path: Path,
-    diskfmt: Literal["h5ad", "zarr"],
-    roundtrip: Callable[[ad.AnnData, Path], ad.AnnData],
+    diskfmt_store: Path | MemoryStore,
+    roundtrip: Callable[[ad.AnnData, Path | MemoryStore], ad.AnnData],
 ) -> None:
     import scanpy as sc
 
@@ -898,7 +872,7 @@ def test_scanpy_krumsiek11(
     # Depending on pd.options.future.infer_string, this becomes either `object` or `'string'`
     orig.var.columns = orig.var.columns.astype(str)
     with ad.settings.override(allow_write_nullable_strings=True):
-        curr = roundtrip(orig, tmp_path / f"test.{diskfmt}")
+        curr = roundtrip(orig, diskfmt_store)
     # These categories are constructed manually in scanpy's code so are not "roundtripped" from disk.
     assert isinstance(orig.obs, pd.DataFrame)
     assert isinstance(curr.obs, pd.DataFrame)
@@ -966,7 +940,7 @@ def _empty_dir_store(tmp_path: Path) -> Path:
     "make_store",
     [
         pytest.param(_empty_dir_store, id="dir"),
-        pytest.param(lambda _: zarr.storage.MemoryStore(), id="memory"),
+        pytest.param(lambda _: MemoryStore(), id="memory"),
     ],
 )
 def test_read_zarr_suggests_nothing(
@@ -979,9 +953,7 @@ def test_read_zarr_suggests_nothing(
     assert not any("Did you mean" in note for note in notes)
 
 
-def test_adata_in_uns(tmp_path, diskfmt, roundtrip):
-    pth = tmp_path / f"adatas_in_uns.{diskfmt}"
-
+def test_adata_in_uns(diskfmt_store, roundtrip):
     orig = gen_adata((4, 5), **GEN_ADATA_NO_XARRAY_ARGS)
     orig.uns["adatas"] = {
         "a": gen_adata((1, 2), **GEN_ADATA_NO_XARRAY_ARGS),
@@ -991,7 +963,7 @@ def test_adata_in_uns(tmp_path, diskfmt, roundtrip):
     another_one.raw = gen_adata((2, 7), **GEN_ADATA_NO_XARRAY_ARGS)
     orig.uns["adatas"]["b"].uns["another_one"] = another_one
 
-    curr = roundtrip(orig, pth)
+    curr = roundtrip(orig, diskfmt_store)
 
     assert_equal(orig, curr)
 
@@ -1008,14 +980,12 @@ def test_adata_in_uns(tmp_path, diskfmt, roundtrip):
         ),
     ],
 )
-def test_none_dict_value_in_uns(diskfmt, tmp_path, roundtrip, uns_val):
+def test_none_dict_value_in_uns(diskfmt_store, roundtrip, uns_val):
     if callable(uns_val):
         uns_val = uns_val()
-    pth = tmp_path / f"adata_dtype.{diskfmt}"
-
     orig = ad.AnnData(np.ones((3, 4)), uns=dict(val=uns_val))
     with ad.settings.override(allow_write_nullable_strings=True):
-        curr = roundtrip(orig, pth)
+        curr = roundtrip(orig, diskfmt_store)
 
     if isinstance(orig.uns["val"], pd.DataFrame):
         pd.testing.assert_frame_equal(curr.uns["val"], orig.uns["val"])
@@ -1023,11 +993,9 @@ def test_none_dict_value_in_uns(diskfmt, tmp_path, roundtrip, uns_val):
         assert curr.uns["val"] == orig.uns["val"]
 
 
-def test_io_dtype(tmp_path, diskfmt, dtype, roundtrip):
-    pth = tmp_path / f"adata_dtype.{diskfmt}"
-
+def test_io_dtype(diskfmt_store, dtype, roundtrip):
     orig = ad.AnnData(np.ones((5, 8), dtype=dtype))
-    curr = roundtrip(orig, pth)
+    curr = roundtrip(orig, diskfmt_store)
 
     assert curr.X.dtype == dtype
 
@@ -1061,7 +1029,7 @@ def test_forward_slash_key(
     getattr(a, elem_key)["bad/key"] = np.ones(
         (10,) if elem_key in ["obs", "var"] else (10, 10)
     )
-    path = tmp_path / f"test.{store_type}"
+    store = tmp_path / "test.h5ad" if store_type == "h5ad" else MemoryStore()
     is_default = disallow_forward_slash_in_h5ad is None
     # default case of unset parameter is to not allow writing of forward slashes as of anndata 0.13
     can_write_slash_key = (
@@ -1083,10 +1051,10 @@ def test_forward_slash_key(
         if can_write_slash_key
         else pytest.raises(ValueError, match=r"Forward slashes"),
     ):
-        getattr(a, f"write_{store_type}")(path)
+        getattr(a, f"write_{store_type}")(store)
 
     # read and check that bad keys were only written if allowed
-    elem = getattr(getattr(ad, f"read_{store_type}")(path), elem_key)
+    elem = getattr(getattr(ad, f"read_{store_type}")(store), elem_key)
     if can_write_slash_key:
         if elem_key in {"obs", "var"}:
             assert "bad/key" in elem
@@ -1114,14 +1082,14 @@ def test_leading_slash_error(
     getattr(a, elem_key)[key] = np.ones(
         (10,) if elem_key in ["obs", "var"] else (10, 10)
     )
-    path = tmp_path / f"test.{store_type}"
+    store = tmp_path / "test.h5ad" if store_type == "h5ad" else MemoryStore()
 
     # “not in the subpath” is raised by e.g. `write_elem(g["z"], "/y", ...)`,
     # while “Forward slashes” is raised earlier by `write_anndata`/`write_h5ad`
     with pytest.raises(ValueError, match=r"not in the subpath|Forward slashes"):
-        getattr(a, f"write_{store_type}")(path)
+        getattr(a, f"write_{store_type}")(store)
 
-    elem = getattr(getattr(ad, f"read_{store_type}")(path), elem_key)
+    elem = getattr(getattr(ad, f"read_{store_type}")(store), elem_key)
     if elem_key in {"obs", "var"}:
         assert set(elem.columns) == {"_index"}
     else:
@@ -1135,20 +1103,18 @@ def test_leading_slash_error(
 @pytest.mark.parametrize(
     "func", [ad.experimental.read_lazy, ad.experimental.read_elem_lazy]
 )
-def test_read_lazy_import_error(func, tmp_path):
-    ad.AnnData(np.ones((10, 10))).write_zarr(tmp_path)
+def test_read_lazy_import_error(func):
+    ad.AnnData(np.ones((10, 10))).write_zarr(store := MemoryStore())
+    g = zarr.open(store)
     with pytest.raises(ImportError, match="xarray"):
-        func(
-            zarr.open(
-                tmp_path if func is ad.experimental.read_lazy else tmp_path / "obs"
-            )
-        )
+        func(g if func is ad.experimental.read_lazy else g["obs"])
 
 
 @pytest.mark.zarr_io
-def test_write_elem_consolidated(tmp_path: Path):
-    ad.AnnData(np.ones((10, 10))).write_zarr(tmp_path)
-    g = zarr.open_group(tmp_path)
+def test_write_elem_consolidated():
+    store = MemoryStore()
+    ad.AnnData(np.ones((10, 10))).write_zarr(store)
+    g = zarr.open_group(store)
     obs = g["obs"]
     assert isinstance(obs, zarr.Group)
     with pytest.raises(
@@ -1158,11 +1124,10 @@ def test_write_elem_consolidated(tmp_path: Path):
 
 
 @pytest.mark.zarr_io
-def test_write_elem_version_mismatch(tmp_path: Path):
-    zarr_path = tmp_path / "foo.zarr"
+def test_write_elem_version_mismatch():
     adata = ad.AnnData(np.ones((10, 10)))
     g = zarr.open_group(
-        zarr_path,
+        MemoryStore(),
         mode="w",
         zarr_format=2 if ad.settings.zarr_write_format == 3 else 3,
     )
diff --git a/tests/test_structured_arrays.py b/tests/test_structured_arrays.py
index bf0c16001..248bdc1e4 100644
--- a/tests/test_structured_arrays.py
+++ b/tests/test_structured_arrays.py
@@ -11,8 +11,11 @@
 from anndata.tests.helpers import gen_vstr_recarray
 
 if TYPE_CHECKING:
+    from pathlib import Path
     from typing import Literal
 
+    from zarr.storage import MemoryStore
+
 
 def assert_str_contents_equal(A, B):
     lA = [
@@ -27,7 +30,10 @@ def assert_str_contents_equal(A, B):
 
 
 def test_io(
-    tmp_path, diskfmt: Literal["zarr", "h5ad"], diskfmt2: Literal["zarr", "h5ad"]
+    diskfmt: Literal["zarr", "h5ad"],
+    diskfmt2: Literal["zarr", "h5ad"],
+    diskfmt_store: Path | MemoryStore,
+    diskfmt2_store: Path | MemoryStore,
 ) -> None:
     from zarr.core.dtype.common import UnstableSpecificationWarning
 
@@ -40,9 +46,6 @@ def test_io(
     read2 = getattr(ad, f"read_{diskfmt2}")
     write2 = lambda adata, pth: getattr(adata, f"write_{diskfmt2}")(pth)
 
-    filepth1 = tmp_path / f"test1.{diskfmt}"
-    filepth2 = tmp_path / f"test2.{diskfmt2}"
-
     str_recarray = gen_vstr_recarray(3, 5)
     u_recarray = str_recarray.astype([(n, "U10") for n in str_recarray.dtype.fields])
     s_recarray = str_recarray.astype([(n, "S10") for n in str_recarray.dtype.fields])
@@ -50,10 +53,10 @@ def test_io(
     initial = AnnData(np.zeros((3, 3)))
     initial.uns = dict(str_rec=str_recarray, u_rec=u_recarray, s_rec=s_recarray)
 
-    write1(initial, filepth1)
-    disk_once = read1(filepth1)
-    write2(disk_once, filepth2)
-    disk_twice = read2(filepth2)
+    write1(initial, diskfmt_store)
+    disk_once = read1(diskfmt_store)
+    write2(disk_once, diskfmt2_store)
+    disk_twice = read2(diskfmt2_store)
 
     adatas = [initial, disk_once, disk_twice]
     keys = [
diff --git a/tests/test_x.py b/tests/test_x.py
index b908f7536..839c70f8e 100644
--- a/tests/test_x.py
+++ b/tests/test_x.py
@@ -151,16 +151,15 @@ def test_copy_view():
 ############
 
 
-def test_io_missing_X(tmp_path, diskfmt):
-    file_pth = tmp_path / f"x_none_adata.{diskfmt}"
+def test_io_missing_X(diskfmt_store, diskfmt):
     write = lambda obj, pth: getattr(obj, f"write_{diskfmt}")(pth)
     read = getattr(ad, f"read_{diskfmt}")
 
     adata = gen_adata((20, 30), **GEN_ADATA_NO_XARRAY_ARGS)
     del adata.X
 
-    write(adata, file_pth)
-    from_disk = read(file_pth)
+    write(adata, diskfmt_store)
+    from_disk = read(diskfmt_store)
 
     assert_equal(from_disk, adata)
 
diff --git a/tests/test_x_layers_2d.py b/tests/test_x_layers_2d.py
index 11102beab..460af685f 100644
--- a/tests/test_x_layers_2d.py
+++ b/tests/test_x_layers_2d.py
@@ -3,13 +3,14 @@
 from __future__ import annotations
 
 import warnings
-from typing import TYPE_CHECKING, Literal
+from typing import TYPE_CHECKING, Literal, cast
 
 import h5py
 import numpy as np
 import pandas as pd
 import pytest
 import zarr
+from zarr.storage import MemoryStore
 
 import anndata as ad
 from anndata.io import write_elem
@@ -109,7 +110,7 @@ def _make_non_conforming(
     *,
     diskfmt: Literal["h5ad", "zarr"],
     which: WhichAttr,
-) -> Path:
+) -> Path | MemoryStore:
     """Build a syntactically-valid AnnData file where exactly one of ``X`` /
     ``layers["L"]`` is non-2-D.
 
@@ -120,6 +121,7 @@ def _make_non_conforming(
     n_obs, n_var = arr3d.shape[:2]
     obs = pd.DataFrame(index=[f"o{i}" for i in range(n_obs)])
     var = pd.DataFrame(index=[f"v{i}" for i in range(n_var)])
+    pth: Path | MemoryStore
     if diskfmt == "h5ad":
         pth = tmp_path / "non_conforming.h5ad"
         # Start from a conforming file so obs/var/encoding are well-formed,
@@ -133,7 +135,7 @@ def _make_non_conforming(
                 write_elem(f, "layers", {"L": arr3d})
         return pth
     if diskfmt == "zarr":
-        pth = tmp_path / "non_conforming.zarr"
+        pth = MemoryStore()
         f = zarr.open_group(pth, mode="w")
         f.attrs.setdefault("encoding-type", "anndata")
         f.attrs.setdefault("encoding-version", "0.1.0")
@@ -157,13 +159,17 @@ def _make_non_conforming(
     raise ValueError(msg)
 
 
-def _read(pth: Path, diskfmt: Literal["h5ad", "zarr"]) -> ad.AnnData:
-    return ad.read_h5ad(pth) if diskfmt == "h5ad" else ad.read_zarr(pth)
+def _read(pth: Path | MemoryStore, diskfmt: Literal["h5ad", "zarr"]) -> ad.AnnData:
+    if diskfmt == "h5ad":
+        return ad.read_h5ad(cast("Path", pth))
+    return ad.read_zarr(pth)
 
 
-def _write(adata: ad.AnnData, pth: Path, diskfmt: Literal["h5ad", "zarr"]) -> None:
+def _write(
+    adata: ad.AnnData, pth: Path | MemoryStore, diskfmt: Literal["h5ad", "zarr"]
+) -> None:
     if diskfmt == "h5ad":
-        adata.write_h5ad(pth)
+        adata.write_h5ad(cast("Path", pth))
     else:
         adata.write_zarr(pth)
 
@@ -200,7 +206,7 @@ def test_read_with_non_2d_warns(
 
 
 def test_write_with_non_2d_raises(
-    tmp_path: Path,
+    diskfmt_store: Path | MemoryStore,
     arr2d: np.ndarray,
     arr3d: np.ndarray,
     diskfmt: Literal["h5ad", "zarr"],
@@ -212,9 +218,8 @@ def test_write_with_non_2d_raises(
     # we're only interested in the write-side raise here.
     with pytest.warns(UserWarning, match=MSG_PATTERN):
         _set_non_2d(adata, which, arr3d)
-    out = tmp_path / f"out.{diskfmt}"
     with pytest.raises(ValueError, match=MSG_PATTERN):
-        _write(adata, out, diskfmt)
+        _write(adata, diskfmt_store, diskfmt)
 
 
 def _set_non_2d(adata: ad.AnnData, which: WhichAttr, value: np.ndarray) -> None:

EOF_R2E_TEST_PATCH
R2E_APPLY_RC=$?
if [ "$R2E_APPLY_RC" -ne 0 ]; then
  echo "0.000000" > /logs/verifier/reward.txt
  printf '%s' '{"reward": 0.0, "resolved": false, "parse_status": "test_patch_apply_failed"}' > /logs/verifier/reward-details.json
  echo "R2E: test_patch failed to apply (rc=$R2E_APPLY_RC) — failing closed" >&2
  exit 0
fi
( . /workspace/.venv/bin/activate && cd /workspace && python -m pytest -v src/anndata/tests/helpers.py tests/conftest.py tests/lazy/conftest.py tests/lazy/test_concat.py tests/lazy/test_read.py tests/test_annot.py tests/test_backed_dense.py tests/test_backed_sparse.py tests/test_base.py tests/test_concatenate_disk.py tests/test_dask.py tests/test_gpu.py tests/test_io_backwards_compat.py tests/test_io_dispatched.py tests/test_io_elementwise.py tests/test_io_partial.py tests/test_io_utils.py tests/test_readwrite.py tests/test_structured_arrays.py tests/test_x.py tests/test_x_layers_2d.py ) > /logs/verifier/test_output.log 2>&1
TEST_EXIT_CODE=$?
cat /logs/verifier/test_output.log
python3 "$SCRIPT_DIR/verifier.py" --log /logs/verifier/test_output.log --f2p "$SCRIPT_DIR/f2p.json" --p2p "$SCRIPT_DIR/p2p.json" --test-cmds '. /workspace/.venv/bin/activate && cd /workspace && python -m pytest -v src/anndata/tests/helpers.py tests/conftest.py tests/lazy/conftest.py tests/lazy/test_concat.py tests/lazy/test_read.py tests/test_annot.py tests/test_backed_dense.py tests/test_backed_sparse.py tests/test_base.py tests/test_concatenate_disk.py tests/test_dask.py tests/test_gpu.py tests/test_io_backwards_compat.py tests/test_io_dispatched.py tests/test_io_elementwise.py tests/test_io_partial.py tests/test_io_utils.py tests/test_readwrite.py tests/test_structured_arrays.py tests/test_x.py tests/test_x_layers_2d.py' --exit-code "$TEST_EXIT_CODE" --out-dir /logs/verifier || { [ "$TEST_EXIT_CODE" -eq 0 ] && echo "1.0" > /logs/verifier/reward.txt || echo "0.0" > /logs/verifier/reward.txt; }
git checkout d75540e9136f3440d5e20be53da69e987bf463a7 -- src/anndata/tests/helpers.py tests/conftest.py tests/lazy/conftest.py tests/lazy/test_concat.py tests/lazy/test_read.py tests/test_annot.py tests/test_backed_dense.py tests/test_backed_sparse.py tests/test_base.py tests/test_concatenate_disk.py tests/test_dask.py tests/test_gpu.py tests/test_io_backwards_compat.py tests/test_io_dispatched.py tests/test_io_elementwise.py tests/test_io_partial.py tests/test_io_utils.py tests/test_readwrite.py tests/test_structured_arrays.py tests/test_x.py tests/test_x_layers_2d.py || true
exit 0

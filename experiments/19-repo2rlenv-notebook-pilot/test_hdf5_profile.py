"""Native format checks on tiny synthetic fixtures, not biological execution."""

import h5py
import numpy as np

from biotasks.data_profile import profile_file


def test_hdf5_metadata_keeps_shape_values_distinct_from_axis_semantics(tmp_path):
    path = tmp_path / "example.h5"
    with h5py.File(path, "w") as source:
        source.create_dataset("dimensions", data=np.array([2000, 4000], dtype="int64"))
        source.create_dataset("counts", shape=(2000, 4000), dtype="float32", chunks=(20, 40))
        source.create_dataset("identifiers", shape=(4000,), dtype=h5py.string_dtype())
        source["external"] = h5py.ExternalLink("not-present.h5", "/values")
    assert path.stat().st_size < 65536
    record = profile_file(tmp_path, path.name)
    structure = record["structure"]
    entries = {item["path"]: item for item in structure["datasets"]}
    assert structure["kind"] == "hdf5"
    assert entries["/dimensions"]["shape"] == [2]
    assert entries["/dimensions"]["values"] == [2000, 4000]
    assert entries["/counts"]["shape"] == [2000, 4000]
    assert "values" not in entries["/counts"] and "values" not in entries["/identifiers"]
    assert "/external" not in entries
    assert structure["axis_semantics"] == "not inferred"
    assert path.stat().st_size < 65536


def test_hdf5_reports_truncation_and_does_not_read_virtual_values(tmp_path):
    path = tmp_path / "bounded.h5"
    with h5py.File(path, "w") as source:
        layout = h5py.VirtualLayout(shape=(2,), dtype="int64")
        layout[:] = h5py.VirtualSource("not-present.h5", "values", shape=(2,))
        source.create_virtual_dataset("a_virtual", layout)
        for number in range(300):
            source.create_dataset(f"data_{number}", shape=(0,), dtype="float32")
    structure = profile_file(tmp_path, path.name)["structure"]
    assert structure["truncated"] is True
    assert len(structure["datasets"]) == 256
    assert "values" not in structure["datasets"][0]

"""No network or package execution: source provenance and read-only boundary."""

import asyncio
import hashlib
import io
import json
import tarfile
import time
import zipfile

import httpx
import pytest
from package_inspection import PackageInspection, inspection_context, package_catalog


def fixture_archive(kind="universal_wheel"):
    buffer = io.BytesIO()
    source = (
        b"# This source is read, never imported\nraise RuntimeError('DO NOT EXECUTE')\n"
        + b"value = 1\n" * 105
    )
    if kind == "universal_wheel":
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("example/core.py", source)
            archive.writestr("../outside.py", b"unsafe")
            archive.writestr("/absolute.py", b"unsafe")
            symlink = zipfile.ZipInfo("link.py")
            symlink.external_attr = 0o120777 << 16
            archive.writestr(symlink, b"/etc/passwd")
    else:
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            record = tarfile.TarInfo("example/core.py")
            record.size = len(source)
            archive.addfile(record, io.BytesIO(source))
            link = tarfile.TarInfo("link.py")
            link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
            archive.addfile(link)
    data = buffer.getvalue()
    spec = {
        "url": "https://files.pythonhosted.org/packages/example.whl",
        "hash": "sha256:" + hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }
    catalog = {"example": {"version": "1.0", "kind": kind, "distribution": spec}}
    return data, catalog, source


@pytest.mark.parametrize("kind", ["universal_wheel", "sdist"])
def test_inspection_preserves_identity_without_extracting_or_executing(tmp_path, kind):
    data, catalog, source = fixture_archive(kind)
    downloads = []

    def fetch(request):
        downloads.append(str(request.url))
        return httpx.Response(200, content=data)

    inspection = PackageInspection(
        catalog, tmp_path / "sources", time.time() + 60, transport=httpx.MockTransport(fetch)
    )

    async def check():
        listing = json.loads(await inspection.list_package_files("example"))
        assert listing["files"] == ["example/core.py"]
        content = json.loads(await inspection.read_package_file("example", "example/core.py", 2, 3))
        assert content["sha256"] == hashlib.sha256(source).hexdigest()
        assert content["total_lines"] == 107
        assert "2: raise RuntimeError" in content["text"]
        first = json.loads(await inspection.search_package("example", "value"))
        second = json.loads(
            await inspection.search_package("example", "value", offset=first["next_offset"])
        )
        assert len(first["matches"]) == 100
        assert len(second["matches"]) == 5 and second["next_offset"] is None
        for path in ("../outside.py", "/etc/passwd", "link.py"):
            result = await inspection.handlers["read_package_file"](package="example", path=path)
            assert "error" in json.loads(result)
        result = await inspection.handlers["list_package_files"](package="not-installed")
        assert "error" in json.loads(result)

    asyncio.run(check())
    assert len(downloads) == 1
    assert not (tmp_path / "outside.py").exists()
    assert not list(tmp_path.rglob("*.py"))


@pytest.mark.parametrize("failure", ["digest", "size", "redirect"])
def test_unverified_archive_never_becomes_available(tmp_path, failure):
    data, catalog, _ = fixture_archive()
    if failure == "digest":
        catalog["example"]["distribution"]["hash"] = "sha256:" + "0" * 64
    if failure == "size":
        catalog["example"]["distribution"]["size"] -= 1
    requests = []

    def fetch(request):
        requests.append(str(request.url))
        return (
            httpx.Response(302, headers={"Location": "http://internal.invalid"})
            if failure == "redirect"
            else httpx.Response(200, content=data)
        )

    inspection = PackageInspection(
        catalog, tmp_path / "sources", time.time() + 60, transport=httpx.MockTransport(fetch)
    )
    result = asyncio.run(inspection.handlers["list_package_files"](package="example"))
    assert "error" in json.loads(result)
    assert len(requests) == 1
    assert sorted(p.name for p in inspection.root.iterdir()) == ["catalog.json"]


def test_catalog_requires_recorded_version_and_supported_pinned_source():
    lock = """[[package]]
name = "Example_Package"
version = "1.0"
wheels = [{url = "https://files.pythonhosted.org/packages/example-1.0-py3-none-any.whl", hash = "sha256:HASH", size = 12}]
[[package]]
name = "other"
version = "2"
sdist = {url = "https://private.invalid/other.tar.gz", hash = "sha256:HASH", size = 12}
""".replace("HASH", "a" * 64)
    catalog = package_catalog(lock, "Example.Package==1.0\nother==2\nmissing==3\n")
    assert catalog["example-package"]["kind"] == "universal_wheel"
    assert catalog["other"]["distribution"] is None
    assert catalog["missing"]["distribution"] is None
    assert package_catalog(lock, "Example.Package==2\n")["example-package"]["distribution"] is None


def test_deadline_is_not_converted_to_model_feedback(tmp_path):
    _, catalog, _ = fixture_archive()
    inspection = PackageInspection(catalog, tmp_path / "sources", time.time() - 1)
    with pytest.raises(TimeoutError):
        asyncio.run(inspection.handlers["list_package_files"](package="example"))


@pytest.mark.parametrize(
    "record",
    [
        "example @ file:///work/checkout",
        "example @ git+https://example.org/repository.git@abc123",
        "example @ https://user:password@example.org/private.whl",
    ],
)
def test_direct_reference_does_not_crash_or_borrow_a_registry_release(record):
    lock = """[[package]]
name = "example"
version = "1.0"
sdist = {url = "https://files.pythonhosted.org/example.tar.gz", hash = "sha256:HASH", size = 12}
""".replace("HASH", "a" * 64)
    catalog = package_catalog(lock, record)
    assert catalog["example"]["version"] is None
    assert catalog["example"]["distribution"] is None
    assert "Direct-reference" in catalog["example"]["unavailable_reason"]
    assert "password" not in json.dumps(catalog)
    assert "example.org" not in json.dumps(catalog)


def test_comments_editables_and_unparsed_records_are_explicit_evidence_gaps():
    environment = "# editable local install\n-e /work/project\ninvalid >>> record\nexample==1.0\n"
    catalog = package_catalog("package = []", environment)
    context = inspection_context(catalog, environment)
    assert list(catalog) == ["example"]
    assert [x["line"] for x in context["unparsed_environment_records"]] == [2, 3]
    assert all(len(x["record_sha256"]) == 64 for x in context["unparsed_environment_records"])
    assert "/work/project" not in json.dumps(context)
    assert "unparsed_environment_records" not in inspection_context(catalog)


@pytest.mark.parametrize(
    "record", ["example", "example>=1", "example==1.*", 'example==1; os_name=="a"']
)
def test_unresolved_versions_are_not_invented_from_the_lock(record):
    catalog = package_catalog('[[package]]\nname="example"\nversion="1.0"\n', record)
    assert catalog["example"]["version"] is None
    assert catalog["example"]["distribution"] is None


def test_conflicting_normalized_installed_identities_are_unavailable():
    catalog = package_catalog("package = []", "Example_Package==1\nexample.package==2\n")
    assert catalog["example-package"]["version"] is None
    assert "ambiguous" in catalog["example-package"]["unavailable_reason"]

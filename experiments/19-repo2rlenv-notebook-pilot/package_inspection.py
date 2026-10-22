"""Read locked package distributions without installing or executing their code."""

import hashlib
import json
import re
import tarfile
import time
import tomllib
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import httpx
from packaging.requirements import InvalidRequirement, Requirement


def normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def installed_records(environment):
    """Read freeze records without inventing versions or following direct URLs."""
    installed, unresolved = {}, []
    for number, raw in enumerate(environment.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            unresolved.append(
                {
                    "line": number,
                    "record_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                    "reason": "Unparsed or editable environment record; installed identity unavailable",
                }
            )
            continue
        name = normalized(requirement.name)
        specs = list(requirement.specifier)
        version, reason = None, None
        if requirement.url:
            reason = "Direct-reference installation; a registry release is not its source evidence"
        elif (
            not requirement.marker
            and not requirement.extras
            and len(specs) == 1
            and specs[0].operator in {"==", "==="}
            and "*" not in specs[0].version
        ):
            version = specs[0].version
        else:
            reason = "No unconditional exact installed version is recorded"
        if name in installed:
            version = None
            reason = "Duplicate environment records; installed identity is ambiguous"
        installed[name] = {"version": version}
        if reason:
            installed[name]["unavailable_reason"] = reason
    return installed, unresolved


def package_catalog(lock, environment):
    """Select release sources only for versions recorded in the actual environment.

    Pure-Python universal wheels expose distributed Python source. Otherwise use
    the locked sdist; it is release source, not proof of the installed binary.
    """
    installed, _ = installed_records(environment)
    catalog = {}
    packages = tomllib.loads(lock)["package"]
    for name, record in installed.items():
        version = record["version"]
        matches = [
            p for p in packages if normalized(p["name"]) == name and p.get("version") == version
        ]
        item = {**record, "distribution": None}
        if version is not None and len(matches) == 1:
            p = matches[0]
            wheels = [
                w for w in p.get("wheels", []) if urlsplit(w["url"]).path.endswith("-none-any.whl")
            ]
            distribution = wheels[0] if len(wheels) == 1 else p.get("sdist")
            if distribution:
                url = urlsplit(distribution["url"])
                # No model-selected URL, credential-bearing registry or redirects.
                if (
                    url.scheme == "https"
                    and url.hostname == "files.pythonhosted.org"
                    and url.port in {None, 443}
                    and not url.username
                    and not url.password
                    and not url.query
                    and not url.fragment
                    and re.fullmatch(r"sha256:[0-9a-f]{64}", distribution["hash"])
                    and type(distribution["size"]) is int
                    and distribution["size"] > 0
                ):
                    item["distribution"] = {
                        key: distribution[key] for key in ("url", "hash", "size")
                    }
                    item["kind"] = "universal_wheel" if distribution in wheels else "sdist"
        catalog[name] = item
    return catalog


def inspection_context(catalog, environment=None):
    context = {
        "packages": catalog,
        "boundary": (
            "Read-only release-source inspection for recorded installed versions. "
            "Archives are hash-verified against the retained reference lock. No installation, "
            "imports, execution, shell, or arbitrary URLs. Universal wheels contain Python "
            "source; sdists are corresponding release source, not evidence of the exact "
            "installed binary or its build options. Direct-reference, editable, ambiguous or "
            "unparsed records do not authorize a registry fallback or arbitrary URL retrieval. "
            "Unavailable source remains an explicit evidence gap."
        ),
    }
    if environment is not None:
        context["unparsed_environment_records"] = installed_records(environment)[1]
    return context


def tool(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


PACKAGE_TOOLS = [
    tool(
        "list_package_files",
        "List archive members for a catalog package; prefix is optional.",
        {"package": {"type": "string"}, "prefix": {"type": "string"}},
        ["package"],
    ),
    tool(
        "search_package",
        "Literal text search in package files, 100 matches per page. Follow next_offset.",
        {
            "package": {"type": "string"},
            "query": {"type": "string"},
            "prefix": {"type": "string"},
            "offset": {"type": "integer", "minimum": 0},
        },
        ["package", "query"],
    ),
    tool(
        "read_package_file",
        "Read an inclusive line range; returns total lines and full file hash.",
        {
            "package": {"type": "string"},
            "path": {"type": "string"},
            "start_line": {"type": "integer", "minimum": 1},
            "end_line": {"type": "integer", "minimum": 1},
        },
        ["package", "path"],
    ),
]


class PackageInspection:
    def __init__(self, catalog, root, deadline, *, transport=None):
        self.catalog, self.root, self.deadline = catalog, root, deadline
        self.transport = transport
        self.root.mkdir(parents=True, exist_ok=False)
        (root / "catalog.json").write_text(json.dumps(inspection_context(catalog), indent=2) + "\n")

    def remaining(self):
        seconds = self.deadline - time.time()
        if seconds <= 0:
            raise TimeoutError("Inspection deadline exhausted")
        return seconds

    async def archive(self, package):
        package = normalized(package)
        item = self.catalog.get(package)
        if not item or not item["distribution"]:
            raise ValueError("No supported locked source distribution for this installed package")
        self.remaining()
        spec = item["distribution"]
        digest = spec["hash"].removeprefix("sha256:")
        path = self.root / (digest + (".whl" if item["kind"] == "universal_wheel" else ".tar.gz"))
        if not path.exists():
            temporary = path.with_suffix(".partial")
            try:
                async with httpx.AsyncClient(
                    transport=self.transport, follow_redirects=False
                ) as client:
                    async with client.stream(
                        "GET", spec["url"], timeout=min(60, self.remaining())
                    ) as response:
                        response.raise_for_status()
                        count, hasher = 0, hashlib.sha256()
                        with temporary.open("wb") as stream:
                            async for chunk in response.aiter_bytes():
                                self.remaining()
                                count += len(chunk)
                                if count > spec["size"]:
                                    raise ValueError("Distribution exceeds locked size")
                                stream.write(chunk)
                                hasher.update(chunk)
                        if count != spec["size"] or hasher.hexdigest() != digest:
                            raise ValueError(
                                "Distribution hash or size differs from reference lock"
                            )
                temporary.rename(path)
            finally:
                temporary.unlink(missing_ok=True)
        # Nothing is extracted to the filesystem; links and unsafe names are excluded.
        if item["kind"] == "universal_wheel":
            return zipfile.ZipFile(path)
        return tarfile.open(path, "r:*")

    @staticmethod
    def members(archive):
        records = (
            archive.infolist() if isinstance(archive, zipfile.ZipFile) else archive.getmembers()
        )
        result = {}
        for record in records:
            name = record.filename if isinstance(archive, zipfile.ZipFile) else record.name
            path = PurePosixPath(name)
            regular = (
                not record.is_dir() and (record.external_attr >> 16) & 0o170000 != 0o120000
                if isinstance(archive, zipfile.ZipFile)
                else record.isfile()
            )
            if regular and not path.is_absolute() and ".." not in path.parts:
                if name in result:
                    raise ValueError("Ambiguous duplicate archive member")
                result[name] = record
        return result

    @staticmethod
    def open_member(archive, record):
        return (
            archive.open(record)
            if isinstance(archive, zipfile.ZipFile)
            else archive.extractfile(record)
        )

    def identity(self, package):
        item = self.catalog[normalized(package)]
        return {"package": normalized(package), **item}

    async def list_package_files(self, package, prefix=""):
        with await self.archive(package) as archive:
            names = sorted(n for n in self.members(archive) if n.startswith(prefix))
        return json.dumps({**self.identity(package), "files": names})

    async def read_package_file(self, package, path, start_line=1, end_line=200):
        if (
            type(start_line) is not int
            or type(end_line) is not int
            or not 1 <= start_line <= end_line
        ):
            raise ValueError("Specify an inclusive positive line range")
        lines, hasher, total = [], hashlib.sha256(), 0
        with await self.archive(package) as archive:
            record = self.members(archive).get(path)
            if record is None:
                raise ValueError("Path is not a regular member of the locked distribution")
            with self.open_member(archive, record) as stream:
                for total, raw in enumerate(stream, 1):
                    self.remaining()
                    hasher.update(raw)
                    line = raw.decode("utf-8")
                    if "\0" in line:
                        raise ValueError("Binary file; no implementation text available")
                    if start_line <= total <= end_line:
                        lines.append(f"{total}: {line.rstrip()}")
        return json.dumps(
            {
                **self.identity(package),
                "path": path,
                "sha256": hasher.hexdigest(),
                "total_lines": total,
                "start_line": start_line,
                "end_line": min(end_line, total),
                "text": "\n".join(lines),
            }
        )

    async def search_package(self, package, query, prefix="", offset=0):
        if not query or type(offset) is not int or offset < 0:
            raise ValueError("Nonempty literal query and nonnegative offset required")
        matches, count = [], 0
        with await self.archive(package) as archive:
            for name, record in sorted(self.members(archive).items()):
                if not name.startswith(prefix):
                    continue
                # Native binaries cannot supply source evidence. Source, documentation,
                # metadata and licenses remain discoverable through listing/reading.
                if PurePosixPath(name).suffix.lower() not in {
                    ".py",
                    ".pyi",
                    ".pyx",
                    ".pxd",
                    ".c",
                    ".h",
                    ".cpp",
                    ".hpp",
                    ".md",
                    ".rst",
                    ".txt",
                    ".toml",
                    ".json",
                    ".r",
                    ".f",
                    ".f90",
                }:
                    continue
                with self.open_member(archive, record) as stream:
                    for number, raw in enumerate(stream, 1):
                        self.remaining()
                        line = raw.decode("utf-8", errors="replace")
                        if query in line:
                            if count >= offset:
                                if len(matches) == 100:
                                    return json.dumps(
                                        {
                                            **self.identity(package),
                                            "matches": matches,
                                            "next_offset": count,
                                        }
                                    )
                                matches.append(
                                    {"path": name, "line": number, "text": line.rstrip()}
                                )
                            count += 1
        return json.dumps({**self.identity(package), "matches": matches, "next_offset": None})

    @property
    def handlers(self):
        import functools

        def checked(handler):
            @functools.wraps(handler)
            async def call(**kwargs):
                try:
                    return await handler(**kwargs)
                except (
                    ValueError,
                    KeyError,
                    TypeError,
                    httpx.HTTPError,
                    tarfile.TarError,
                    zipfile.BadZipFile,
                ) as error:
                    return json.dumps(
                        {
                            "error": type(error).__name__,
                            "message": "Source inspection unavailable for these arguments; check the catalog, member path and range. "
                            "No content was accepted from an unverified archive. Report unresolved evidence if necessary.",
                        }
                    )

            return call

        return {
            tool["function"]["name"]: checked(getattr(self, tool["function"]["name"]))
            for tool in PACKAGE_TOOLS
        }

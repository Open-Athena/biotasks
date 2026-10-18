from pathlib import Path
import hashlib
license_file=Path('LICENSE');license_source=Path('LICENSE.rst');data=license_source.read_bytes()
assert (license_file.is_symlink() and license_file.readlink()==Path('LICENSE.rst')) or (license_file.is_file() and license_file.read_bytes()==data)
if license_file.is_symlink():license_file.unlink()
license_file.write_bytes(data)
fixture=Path('Tests/GenBank/origin_line.gb')
if not fixture.exists():fixture=Path('r2e_tests/Tests/GenBank/origin_line.gb')
if not fixture.exists():fixture=Path('GenBank/origin_line.gb')
raw=fixture.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a188b26e7d7f9126e1ff4d6f3c4c5db1bd0788c3c5073c9727e9dc4ab504019e'
Path('GenBank').mkdir(exist_ok=True)
Path('GenBank/origin_line.gb').write_bytes(raw)

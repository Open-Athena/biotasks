"""Our own fixture's recorded build command: compile current tracked source."""
import subprocess
import sysconfig

subprocess.run([
    "/usr/bin/cc", "-shared", "-fPIC", "-O0",
    "-I" + sysconfig.get_paths()["include"],
    "core.c", "-o", "bt60_core" + sysconfig.get_config_var("EXT_SUFFIX"),
], check=True, timeout=20)

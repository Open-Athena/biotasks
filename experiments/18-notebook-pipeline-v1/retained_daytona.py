"""Retain only this run's sandboxes until its exported evidence is verified."""

import json
import os
import shlex
from pathlib import Path

from harbor.environments.daytona import DaytonaEnvironment


class RetainedDaytona(DaytonaEnvironment):
    async def start(self, force_build):
        try:
            await super().start(force_build)
            probe = Path(__file__).with_name("network_probe.py").read_text()
            result = await self.exec(command="python3 -c " + shlex.quote(probe), timeout_sec=30)
            if result.return_code:
                raise RuntimeError("Environment network/resource probe failed")
            evidence = json.loads(result.stdout)
            path = Path(os.environ["BIOTASKS_OWNED_SANDBOXES"]).with_name(
                "network-preflights.jsonl"
            )
            with path.open("a") as out:
                out.write(json.dumps({"id": self._sandbox.id, **evidence}) + "\n")
            if (
                not evidence["network_denied"]
                or evidence["inference_credentials_present"]
                or evidence["gpu_devices"]
            ):
                raise RuntimeError("Environment isolation preflight failed")
            inventory = """import importlib.metadata,json,platform,shutil,subprocess,os
from pathlib import Path
result={'python_version':platform.python_version(),'python_packages':sorted(
    [{'name':d.metadata.get('Name','unknown'),'version':d.version}
     for d in importlib.metadata.distributions()],key=lambda d:d['name'].lower())}
for name,args in [
    ('os_packages',['dpkg-query','-W','-f=${Package}\\t${Version}\\n']),
    ('r_packages',['Rscript','--vanilla','-e',
     'write.table(installed.packages()[,c("Package","Version","Built")],row.names=FALSE,sep="\\t",quote=FALSE)'])]:
    if not shutil.which(args[0]):
        result[name]={'status':'tool_not_installed'}
        continue
    try:
        run=subprocess.run(args,capture_output=True,text=True,timeout=20)
        result[name]={'exit_code':run.returncode,'table':run.stdout,'stderr':run.stderr}
    except subprocess.TimeoutExpired:
        result[name]={'status':'inventory_timeout'}
result['os_release']=Path('/etc/os-release').read_text() if Path('/etc/os-release').exists() else None
s=os.statvfs('/')
result['filesystem_used_bytes_at_start']=(s.f_blocks-s.f_bfree)*s.f_frsize
result['filesystem_measurement_is_peak']=False
print(json.dumps(result))
"""
            packages = await self.exec(
                command="python3 -c " + shlex.quote(inventory), timeout_sec=50
            )
            if packages.return_code:
                raise RuntimeError("Environment package inventory failed")
            with path.with_name("package-manifests.jsonl").open("a") as out:
                out.write(json.dumps({"id": self._sandbox.id, **json.loads(packages.stdout)}) + "\n")
        finally:
            if self._sandbox is not None:
                path = Path(os.environ["BIOTASKS_OWNED_SANDBOXES"])
                with path.open("a") as out:
                    out.write(json.dumps({"id": self._sandbox.id}) + "\n")

    async def stop(self, delete):
        if self._sandbox is not None:
            record = {
                "id": self._sandbox.id,
                "requested_cpu": self._effective_cpus,
                "requested_memory_mb": self._effective_memory_mb,
                "requested_storage_mb": self._effective_storage_mb,
            }
            script = """import json,os
from pathlib import Path
names=['cpu.max','cpu.stat','memory.max','memory.peak','memory.events']
result={n:(Path('/sys/fs/cgroup')/n).read_text().strip() for n in names if (Path('/sys/fs/cgroup')/n).exists()}
s=os.statvfs('/')
result['filesystem_total_bytes']=s.f_blocks*s.f_frsize
result['filesystem_available_bytes']=s.f_bavail*s.f_frsize
result['filesystem_used_bytes_at_stop']=(s.f_blocks-s.f_bfree)*s.f_frsize
result['filesystem_measurement_is_peak']=False
print(json.dumps(result))
"""
            try:
                result = await self.exec(
                    command="python3 -c " + shlex.quote(script), timeout_sec=10
                )
                record["measurements"] = (
                    json.loads(result.stdout) if not result.return_code else None
                )
                record["probe_exit_code"] = result.return_code
            except Exception as error:
                record["probe_error_type"] = type(error).__name__
            with (
                Path(os.environ["BIOTASKS_OWNED_SANDBOXES"])
                .with_name("sandbox-resources.jsonl")
                .open("a") as out
            ):
                out.write(json.dumps(record) + "\n")
        # Direct single-container mode only. The campaign rejects compose tasks.
        await super().stop(delete=False)

import subprocess
files=set()
for args in [['git','diff','--name-only','HEAD'],['git','ls-files','--others','--exclude-standard']]:
 files.update(subprocess.check_output(args,text=True).splitlines())
print('Linting',len(files),'changed/new files',flush=True)
subprocess.run(['./infra/pre-commit.py','--fix',*sorted(files)],check=True)

"""Build the methods-first workbench from the normalized explorer data."""
from pathlib import Path
root = Path(__file__).resolve().parent
source = (root/'explorer.html').read_text()
payload = source.split('window.BIOTASKS_DATA=',1)[1].split(';</script>',1)[0]
(root/'workbench.html').write_text((root/'workbench.template.html').read_text().replace('__PAYLOAD__',payload))
print('Built methods-first workbench with full candidate metadata')

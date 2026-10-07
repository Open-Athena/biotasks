"""Build distinct interaction layouts using the current explorer payload."""
from pathlib import Path
root = Path(__file__).resolve().parent
source = (root/'explorer.html').read_text()
payload = source.split('window.BIOTASKS_DATA=',1)[1].split(';</script>',1)[0]
page = (root/'layout-options.template.html').read_text().replace('__PAYLOAD__',payload)
(root/'layout-options.html').write_text(page)
print('Built five structural layout options')

"""Build four switchable presentations of the same explorer; no network access."""
from pathlib import Path

root = Path(__file__).resolve().parent
page = (root / 'explorer.html').read_text()
css = (root / 'style-options.css').read_text()
picker = '''<aside class="style-picker" aria-label="Choose a visual style"><strong>Four styles · the same 100 documents</strong><p>Switch styles, then explore Sources or Coverage to compare readability. These are design options; the current explorer is unchanged.</p><div class="choices">
<button data-theme="editorial" aria-pressed="true">01 · Editorial<small>Quiet typography · warm paper · report layout</small></button>
<button data-theme="atlas" aria-pressed="false">02 · Atlas<small>Bright blue · spacious cards · dashboard layout</small></button>
<button data-theme="console" aria-pressed="false">03 · Lab console<small>Dark surface · compact rows · technical typography</small></button>
<button data-theme="botanical" aria-pressed="false">04 · Botanical<small>Sage and cream · soft forms · serif headings</small></button>
</div></aside>'''
script = '''<script>
for(const button of document.querySelectorAll('[data-theme]')) button.onclick=()=>{
 document.body.dataset.style=button.dataset.theme;
 for(const option of document.querySelectorAll('[data-theme]')) option.setAttribute('aria-pressed',String(option===button));
};
</script>'''
page = page.replace('</head>', '<style>'+css+'</style></head>').replace('<body>', '<body data-style="editorial">'+picker).replace('</body>',script+'</body>')
(root / 'style-options.html').write_text(page)
print('Built four style options with unchanged candidate payload')

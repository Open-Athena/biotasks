"""Check explorer sections, navigation, filtering and responsive overview."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/home/exedev/.local/bin/chromium', headless=True,
        args=['--disable-gpu-compositing', '--disable-software-rasterizer', '--use-gl=disabled', '--single-process', '--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-dev-shm-usage', '--disable-extensions', '--renderer-process-limit=1', '--js-flags=--max-old-space-size=96'])
    try:
        page=browser.new_page(viewport={'width':1120,'height':900})
        page.context.set_offline(True)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((root/'index.html').as_uri())
        assert page.locator('#approaches').is_visible()
        assert page.locator('#notebook-directory').is_hidden()
        assert page.locator('.approach-flow li').count()==8
        assert page.locator('#approach-seta').is_visible()
        assert page.locator('#approach-bix').is_hidden()
        assert page.locator('.authoring-prompt').count()==3
        assert page.locator('.authoring-prompt .artifact-scroll').first.evaluate('e=>e.scrollHeight>e.clientHeight')
        assert page.get_by_text('Does the authoring model see the notebook?',exact=False).is_visible()
        page.select_option('#approach-select','bix')
        assert page.locator('#approach-seta').is_hidden()
        assert page.locator('#approach-bix').is_visible()
        assert page.get_by_text('Exact prompt not located',exact=False).is_visible()
        page.reload()
        assert page.locator('#approach-select').input_value()=='bix'
        page.click('#browse-notebooks')
        assert page.locator('#notebook-directory').is_visible()
        page.select_option('#origin','BixBench')
        assert page.locator('#list tr').count()==1
        page.reload()
        assert page.locator('#notebook-directory').is_visible()
        assert page.locator('#list tr').count()==1
        page.click('#show-approaches')
        assert page.locator('#approaches').is_visible()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path='/tmp/bio17-attempts/approaches-mobile.png')
        page.select_option('#approach-select','seta')
        assert page.locator('.authoring-prompt').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors,errors
        print('PASS: default overview, eight stages, disclosure, tabs, filtering, reload, mobile width')
    finally:
        browser.close()

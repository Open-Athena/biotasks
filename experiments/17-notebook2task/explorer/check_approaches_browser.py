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
        assert page.locator('#seta-step-2').is_visible()
        assert page.locator('.authoring-prompt:visible').count()==1
        page.select_option('#seta-prompt-component','1')
        assert 'Shared idea-agent instructions' in page.locator('.authoring-prompt:visible > h2').inner_text()
        page.click('#seta-step-button-3')
        assert page.locator('#seta-step-2').is_hidden()
        assert 'Task-package builder' in page.locator('.authoring-prompt:visible > h2').inner_text()
        page.reload()
        assert page.locator('#seta-step-3').is_visible()
        page.click('#seta-step-button-1')
        assert page.locator('.authoring-prompt:visible').count()==0
        page.locator('#seta-step-button-4').focus()
        page.keyboard.press('Enter')
        assert page.locator('#seta-step-4').is_visible()
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
        page.click('#seta-step-button-2')
        assert page.locator('.authoring-prompt:visible').count()==1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors,errors
        print('PASS: stage selection, prompt-component selection, keyboard, persistence, both approaches, notebook filters, mobile width')
    finally:
        browser.close()

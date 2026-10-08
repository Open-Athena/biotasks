"""Focused offline checks for the bundled SETA/BixBench trace and annotations."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
case = sys.argv[1] if len(sys.argv) > 1 else 'seta-cytopathology'
assert case in ['seta-cytopathology', 'bix-asxl1']
bix = case == 'bix-asxl1'
errors = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/home/exedev/.local/bin/chromium', headless=True,
        args=['--disable-gpu-compositing', '--disable-software-rasterizer', '--use-gl=disabled', '--single-process', '--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-dev-shm-usage', '--disable-extensions', '--renderer-process-limit=1', '--js-flags=--max-old-space-size=96'])
    try:
        page = browser.new_page(viewport={'width': 1120, 'height': 900})
        page.context.set_offline(True)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto((root/'notebooks'/f'{case}.html').as_uri(), wait_until='domcontentloaded')
        from urllib.parse import urlsplit,parse_qs
        assert parse_qs(urlsplit(page.locator('#back').get_attribute('href')).fragment)['view']==['notebooks']
        if bix:
            page.click('#tab-task')
            assert '/workspace/answer.txt' in page.locator('[aria-label="Task prompt"]').inner_text()
            assert '<answer>' in page.locator('[aria-label="Task prompt"]').inner_text()
            assert 'OPEN_ENDED_EVAL_PROMPT' in page.locator('[aria-label="Verifier code or reference record"]').inner_text()
            assert 'openai==2.14.0' in page.locator('[aria-label="Verifier launcher"]').inner_text()
            assert '0.0002' in page.locator('[aria-label="Reference-answer record"]').inner_text()
            assert 'Executable verifier unavailable' not in page.locator('#workspace-panel').inner_text()
        page.click('#tab-solution')
        frame = page.frame_locator('#trace-frame')
        frame.locator('[data-slot=atif-trace-step]').first.wait_for(timeout=15000)
        assert frame.locator('[data-slot=atif-trace-step]').count() == (29 if bix else 10)
        assert ('Unscored' if bix else '1') in page.locator('#attempt-record .metrics').inner_text()
        assert page.locator('#attempt-review-title').inner_text() == 'Summary & annotations'
        assert page.locator('[aria-labelledby=attempt-review-title] h3').count() == 4
        frame.get_by_label('Show setup messages').check()
        assert frame.locator('[data-slot=atif-trace-step]').count() == (31 if bix else 12)
        frame.get_by_label('Show setup messages').uncheck()
        search = frame.get_by_placeholder('e.g. DESeq2, error, simplify')
        search.fill('no-such-step-xyz')
        assert frame.get_by_text('No matching steps.', exact=False).is_visible()
        search.fill('')
        tool = frame.locator('[data-slot=atif-tool-call]').first
        tool.locator('button').first.click()
        assert tool.locator('[data-slot=atif-tool-call-arguments]').is_visible()
        assert tool.locator('[data-slot=atif-tool-call-results]').is_visible()
        assert tool.locator('.trace-code').evaluate('(el) => getComputedStyle(el).color') == 'rgb(248, 248, 242)'
        assert tool.locator('.trace-code .token').count() > 0
        page.screenshot(path=f'/tmp/bio17-attempts/{case}-annotations-desktop.png')
        frame.get_by_label('Group intermediate steps').check()
        assert frame.locator('[data-slot=atif-trace]').count() == 1
        if not bix:
            page.select_option('#task-select', 'own')
            assert page.locator('#trace-frame').count() == 0
            assert 'No independent LLM solver attempts' in page.locator('#workspace-panel').inner_text()
            page.select_option('#task-select', 'released')
        frame.get_by_label('Group intermediate steps').uncheck()
        page.set_viewport_size({'width':390,'height':844})
        frame.locator('[data-slot=atif-trace-step]').first.wait_for()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert frame.locator('body').evaluate('el => el.scrollWidth <= innerWidth')
        page.screenshot(path=f'/tmp/bio17-attempts/{case}-annotations-mobile.png')
        page.click('#back')
        assert page.locator('#notebook-directory').is_visible()
        assert page.locator('#approaches').is_hidden()
        assert not errors, errors
        print('PASS: offline trace, setup toggle, search, tool arguments/results, recipe isolation, mobile width; no page errors')
    finally:
        browser.close()

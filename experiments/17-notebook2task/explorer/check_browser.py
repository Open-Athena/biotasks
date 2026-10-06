"""Focused explorer interaction checks; requires an existing Playwright/Chromium."""
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
url = sys.argv[1] if len(sys.argv) > 1 else (root / 'index.html').as_uri()
errors = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM', '/home/exedev/.local/bin/chromium'), headless=True, args=['--single-process', '--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-gpu-compositing', '--disable-software-rasterizer', '--use-gl=disabled', '--renderer-process-limit=1', '--disable-extensions'])
    try:
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
        if url.startswith('file:'):
            page.context.set_offline(True)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='networkidle', timeout=45000)
        page.wait_for_selector('#list .card')
        assert page.locator('#list .card').count() == 12
        assert 'Airway' in page.locator('#detail h2').inner_text()
        ids = page.evaluate('window.NOTEBOOK_CATALOG.sources.map(r => r.id)')
        assert 'ag-atlas' not in ids and 'pbmc3k' not in ids
        assert 'multiome' in ids
        page.select_option('#group', 'gReLU')
        assert page.locator('#list .card').count() == 3
        with page.expect_download() as event:
            page.click('#export')
        exported = json.loads(Path(event.value.path()).read_text())
        assert len(exported['sources']) == 3
        assert all(x['group'] == 'gReLU' for x in exported['sources'])
        page.click('#reset')
        page.select_option('#role', 'Start here')
        assert page.locator('#list .card').count() == 3
        page.click('#reset')
        page.fill('#search', 'zzzz-no-such-analysis')
        assert page.locator('#list .card').count() == 0
        assert 'No matching' in page.locator('#detail').inner_text()
        page.click('#reset')
        for group in ['Scanpy', 'DESeq2', 'bedtools', 'AlphaGenome', 'gReLU']:
            page.select_option('#group', group)
            n = page.locator('#list .card').count()
            for i in range(n):
                page.locator('#list .card').nth(i).click()
                assert page.locator('#detail h2').inner_text()
                assert 'Not generated' in page.locator('#detail').inner_text()
                assert page.locator('#list .card[aria-pressed=true]').count() == 1
        page.click('#reset')
        page.locator('#list .card').first.click()
        page.screenshot(path='/tmp/biotasks17-desktop.png', full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.select_option('#group', 'AlphaGenome')
        assert page.locator('#list .card').count() == 2
        page.screenshot(path='/tmp/biotasks17-mobile.png', full_page=True)
        assert page.locator('#comparison-select option').count() == 2
        page.select_option('#comparison-select', 'bix-asxl1')
        assert 'DESeq2' in page.locator('.released-task:not(.baseline-output)').inner_text()
        page.click('#comparison-notebook')
        frame = page.frame_locator('#comparison-frame iframe')
        assert frame.locator('section').count() == 17
        assert '~sex+condition' in frame.locator('body').inner_text()
        page.get_by_text('Published reference answer (evaluation material)', exact=True).click()
        assert '0.0002' in page.locator('#comparison-detail details').first.inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width':1280,'height':900})
        page.locator('#comparisons').scroll_into_view_if_needed()
        page.screenshot(path='/tmp/biotasks17-comparisons.png')
        page.get_by_text('Read the actual baseline output', exact=True).click()
        assert 'EARLY_DITCH' in page.locator('.baseline-output').inner_text()
        page.select_option('#comparison-select', 'seta-cytopathology')
        assert 'AUC of at least 0.93' in page.locator('.released-task:not(.baseline-output)').inner_text()
        assert page.locator('#comparison-frame iframe').count() == 0
        page.get_by_text('Read the actual baseline output', exact=True).click()
        assert 'frozen' in page.locator('.baseline-output').inner_text()
        page.get_by_text('Read GLM baseline output', exact=True).click()
        assert 'three distinct model families' in page.locator('.glm-output').inner_text()
        page.select_option('#comparison-select', 'bix-asxl1')
        assert 'output_limit' in page.locator('#comparison-detail').inner_text()
        page.get_by_text('Read GLM baseline output', exact=True).click()
        assert 'No draft or final response' in page.locator('.glm-output').inner_text()
        assert not errors, errors
        print(json.dumps({'url':url,'status':'passed','candidates':12,'checks':['all detail cards','repository and role filters','empty search','reset','filtered JSON export','desktop layout','390px layout without overflow','two released-task comparisons','17-cell offline notebook','published answer disclosure'],'page_errors':errors}))
    finally:
        browser.close()

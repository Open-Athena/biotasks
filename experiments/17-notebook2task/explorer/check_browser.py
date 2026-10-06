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
    browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM', '/home/exedev/.local/bin/chromium'), headless=True, args=['--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-gpu-compositing', '--disable-software-rasterizer', '--use-gl=disabled', '--renderer-process-limit=1', '--disable-extensions'])
    try:
        page = browser.new_page(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
        if url.startswith('file:'):
            page.context.set_offline(True)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='networkidle', timeout=45000)
        page.wait_for_selector('#list .card')
        assert page.locator('#list .card').count() == 14
        assert 'Atlas' in page.locator('#detail h2').inner_text()
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
        assert page.locator('#list .card').count() == 3
        page.screenshot(path='/tmp/biotasks17-mobile.png', full_page=True)
        assert not errors, errors
        print(json.dumps({'url':url,'status':'passed','candidates':14,'checks':['all detail cards','repository and role filters','empty search','reset','filtered JSON export','desktop layout','390px layout without overflow'],'page_errors':errors}))
    finally:
        browser.close()

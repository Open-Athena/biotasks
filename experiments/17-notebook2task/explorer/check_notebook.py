"""Check every author-hosted full-source embed, using one browser/page serially."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
catalog = json.loads((root / 'catalog.json').read_text())
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/home/exedev/.local/bin/chromium', headless=True, args=['--no-sandbox', '--disable-gpu', '--no-zygote', '--disable-gpu-compositing', '--disable-software-rasterizer', '--use-gl=disabled', '--renderer-process-limit=1'])
    try:
        page = browser.new_page(viewport={'width':1280,'height':900})
        page.goto(sys.argv[1] if len(sys.argv)>1 else (root/'index.html').as_uri(), wait_until='domcontentloaded')
        page.wait_for_selector('#list .card')
        for row in catalog['sources']:
            page.select_option('#group', row['group'])
            page.locator('#list .card').filter(has_text=row['title']).click()
            assert page.get_by_role('link', name='Original tutorial / documentation').get_attribute('href') == row['read_url']
            assert page.get_by_role('link', name='Original source on GitHub').get_attribute('href') == row['source_url']
            page.click('#toggle-source')
            frame = page.frame_locator('#frame-slot iframe')
            try:
                frame.locator('pre').first.wait_for(state='attached', timeout=20000)
                frame.locator('pre:visible').first.wait_for(state='visible', timeout=15000)
                body = frame.locator('body').inner_text()
                assert len(body)>1000 and '503 Service Unavailable' not in body
                assert page.locator('#proposal-detail').is_hidden()
                if row['id']=='multiome':
                    assert 'NeurIPS' in body
                    page.locator('#frame-slot').scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    page.screenshot(path='/tmp/biotasks17-current-tutorial.png')
                results.append({'id':row['id'],'url':row['read_url'],'status':'passed'})
            except Exception as exc:
                results.append({'id':row['id'],'url':row['read_url'],'status':'failed','error':str(exc)[:250]})
            print(json.dumps(results[-1]), flush=True)
            page.click('#toggle-source')
            assert page.locator('#proposal-detail').is_visible()
    finally:
        browser.close()
assert all(r['status']=='passed' for r in results), results

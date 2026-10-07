"""Bounded browser checks for the four presentation options."""
import json
import os
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
url = sys.argv[1] if len(sys.argv) > 1 else (root/'layout-options.html').as_uri()
def guard(start=False):
    available = next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    assert available >= (2.5 if start else 2)*1024**3
    assert os.getloadavg()[0] < (1.5 if start else 2.5)
    if start: assert available-450*1024**2 >= 2*1024**3

guard(True)
started=datetime.now(timezone.utc).isoformat()
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/home/exedev/.local/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--renderer-process-limit=1'])
    try:
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url,wait_until='networkidle',timeout=25000)
        for layout in ['catalog','dashboard','coverage','report','workbench']:
            page.locator(f'[data-layout={layout}]').click()
            assert page.locator('h1 br').count()==0
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(layout,width)
            page.set_viewport_size({'width':1440,'height':1000})
            page.screenshot(path=f'/tmp/biotasks16-layout-{layout}.png')
            if layout=='dashboard':page.locator('nav [data-view=sources]').click()
            if layout=='coverage':
                page.locator('[data-route=bioconductor][data-domain=transcriptomics]').click()
                assert page.locator('#route').input_value()=='bioconductor'
                assert page.locator('#domain').input_value()=='transcriptomics'
                page.locator('#reset').click()
            page.locator('#assessment').select_option('apparently_suitable')
            if layout=='workbench':
                assert page.locator('[data-select]').count()==70
                page.locator('[data-select]').nth(1).click()
                assert page.locator('#inspector h2').inner_text()==page.locator('[data-select][aria-pressed=true]').inner_text().split('\n')[0]
            else:
                assert page.locator('[data-source]').count()==70
                page.locator('[data-source]').first.click()
                assert page.locator('#detail').is_visible()
                assert 'Inputs' in page.locator('#detail').inner_text()
                page.locator('#closeDetail').click()
                with page.expect_download() as download:page.locator('#export').click()
                import csv
                assert len(list(csv.DictReader(Path(download.value.path()).open())))==70
            page.locator('#query').fill('no-match-938715')
            assert page.locator('.empty').count()==1
            page.locator('#reset').click()
            page.set_viewport_size({'width':390,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(layout,'filtered view')
            guard()
        assert not errors,errors
    finally:
        browser.close()
print(json.dumps({'url':url,'start':started,'end':datetime.now(timezone.utc).isoformat(),'exit_status':0,'layouts':5,'checks':['five distinct entry layouts','natural heading wrapping','desktop and mobile overflow','70 suitable records in each layout','source evidence modal and persistent inspector','coverage drilldown','CSV exports','empty state and reset'],'page_errors':errors,'estimated_working_set_mib':450,'max_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss},indent=2))

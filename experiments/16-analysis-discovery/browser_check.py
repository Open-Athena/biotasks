"""Bounded UI smoke check. Requires Playwright; never executes source notebooks."""
import csv
import io
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
url = sys.argv[1] if len(sys.argv)>1 else (ROOT/'explorer.html').as_uri()

def resources():
    available = next(int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))
    load = os.getloadavg()[0]
    return available,load

available,load=resources()
assert available >= 2.5*1024**3 and available-450*1024**2 >= 2*1024**3 and load<1.5,(available,load)
manifest=json.loads((ROOT/'candidates.json').read_text())
stage_corrections=json.loads((ROOT/'evidence/legacy-review-stages.json').read_text())
for r in manifest:r.setdefault('review_stage',stage_corrections.get(r['id'],'static_inspection'))
summary=json.loads((ROOT/'summary.json').read_text())
expected_count=len(manifest)
started=datetime.now(timezone.utc).isoformat(); checks=[]; errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/home/exedev/.local/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--renderer-process-limit=1'])
    try:
        page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url,wait_until='networkidle',timeout=25000)
        page.locator('#resultCount').wait_for(state='attached',timeout=10000)
        assert page.locator('#stats .stat strong').all_text_contents()==[str(expected_count),str(summary['all']['reviewed']),str(summary['all']['statuses']['apparently_suitable']),'0']
        page.locator('button[data-tab=sources]').click()
        assert page.locator('#rows > tr').count()==expected_count
        page.locator('#route').select_option('kaggle')
        assert page.locator('#rows > tr').count()==sum(r['route']=='kaggle' for r in manifest)
        page.locator('#cohort').select_option('competition_first')
        page.locator('#assessment').select_option('apparently_suitable')
        assert page.locator('#rows > tr').count()==7
        with page.expect_download() as d: page.locator('#export').click()
        exported=list(csv.DictReader(io.StringIO(Path(d.value.path()).read_text())))
        assert {r['id'] for r in exported}=={'K01','K03','K04','K05','K07','K08','K09'}
        checks.append('Frozen Kaggle cohort filters and exact exported IDs')
        page.locator('#reset').click();page.locator('#review_stage').select_option('access_only')
        assert page.locator('#rows .source-title').count()==sum(r.get('review_stage')=='access_only' for r in manifest)
        page.locator('#reset').click();page.locator('#review_stage').select_option('identified')
        assert page.locator('#rows .source-title').count()==sum(r.get('review_stage')=='identified' for r in manifest)
        page.locator('button[data-tab=overview]').click();page.locator('#showExpansion').click()
        assert page.locator('#rows > tr').count()==60
        page.locator('#reset').click();page.locator('#search').fill('L27');page.locator('#rows summary').click()
        assert 'Performance guidance' in page.locator('#rows').inner_text()
        checks.append('Expansion drilldown, legacy access-only and empty identified-stage filters and recovered exclusion evidence')
        page.locator('#reset').click();page.locator('#search').fill('EBImage')
        assert page.locator('#rows > tr').count()==1
        page.locator('#rows summary').click()
        assert 'nuclei.tif' in page.locator('#rows').inner_text()
        page.locator('#reset').click();page.locator('[data-sort=title]').click()
        titles=page.locator('.source-title').all_text_contents(); assert len(titles)==expected_count
        page.locator('[data-sort=title]').click()
        assert page.locator('.source-title').all_text_contents()==list(reversed(titles))
        page.locator('#search').fill('nothing-matches-this-123');assert page.locator('.empty').count()==1
        checks.append('Search, detail expansion, sort interaction and empty state')
        page.locator('button[data-tab=coverage]').click()
        assert page.locator('#matrix tbody tr').count()==13
        groups=sorted({r['route']+' / '+r['cohort'] for r in json.loads((ROOT/'candidates.json').read_text())})
        assert page.locator('#matrix td').count()==13*len(groups)
        for b in page.locator('#matrix button').all():
            group=groups[int(b.get_attribute('data-group'))]; domain=b.get_attribute('data-domain')
            members=[r for r in manifest if r['route']+' / '+r['cohort']==group and domain in r['subdomains']]
            good=sum(r['assessment']=='apparently_suitable' for r in members)
            assert b.inner_text()==f"{good} / {sum(r.get('review_stage', 'static_inspection') == 'static_inspection' for r in members)}"
        cells=page.locator('#matrix [data-domain="metabolomics"]')
        for i in range(cells.count()):
            cell=cells.nth(i)
            if cell.inner_text().strip()=='1 / 1':cell.click();break
        assert 'metabolomics'==page.locator('#domain').input_value()
        checks.append('Coverage matrix shape and cell drilldown')
        page.locator('button[data-tab=curated]').click();page.locator('#showAwesome').click()
        assert page.locator('#rows > tr').count()==4
        page.locator('button[data-tab=overview]').click()
        page.screenshot(path='/tmp/biotasks16-explorer-desktop.png',full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path='/tmp/biotasks16-explorer-mobile.png',full_page=True)
        page.locator('button[data-tab=sources]').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if url.startswith('file:'):
            page.context.set_offline(True);page.reload(wait_until='load')
            assert page.locator('#stats .stat').count()==4
            checks.append('Offline reload')
        checks.append('Curated drilldown, desktop and 390px mobile layouts')
        available,load=resources();assert available>=2*1024**3 and load<=2.5,(available,load)
        assert not errors,errors
    finally:browser.close()
print(json.dumps({'url':url,'start':started,'end':datetime.now(timezone.utc).isoformat(),'checks':checks,'page_errors':errors,'max_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'estimated_working_set_mib':450,'final_available_bytes':available,'final_load1':load},indent=2))

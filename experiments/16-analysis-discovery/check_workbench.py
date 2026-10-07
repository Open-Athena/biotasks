"""Bounded browser checks for the four presentation options."""
import json
import os
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
url = sys.argv[1] if len(sys.argv) > 1 else (root/'workbench.html').as_uri()
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
        assert page.locator('h1').inner_text()=='How we discover useful analyses'
        assert page.locator('.choices [data-layout]').all_text_contents()==['Methods','Sources','Collection composition','Source index']
        assert page.locator('[data-method-route]').count()==11
        assert 'not only 12 notebooks available on GitHub' in page.locator('#candidateDefinition').inner_text()
        assert page.locator('#hfSurfaces tbody tr').count()==3
        assert page.locator('#hfSurfaces').get_attribute('open') is None
        assert page.locator('#toolProvenance tbody tr').count()==4
        assert '24 of 28' in page.locator('#toolProvenance').inner_text()
        assert page.locator('.method-flow article').count()==4
        with page.expect_download() as download:page.locator('#downloadAll').click()
        exported=json.loads(Path(download.value.path()).read_text())
        assert len(exported)==100
        assert exported==page.evaluate('window.BIOTASKS_DATA.rows')
        for mode in ['methods','workbench','coverage','curated']:
            page.locator(f'.choices [data-layout={mode}]').click()
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(mode,width)
            page.set_viewport_size({'width':1440,'height':1000})
            page.screenshot(path=f'/tmp/biotasks16-workbench-{mode}.png')
            guard()
        page.locator('[data-layout=methods]').click()
        for route in page.evaluate('Object.keys(window.BIOTASKS_DATA.summary.routes)'):
            page.locator(f'[data-method-route="{route}"]').click()
            count=sum(r['route']==route for r in exported)
            assert page.locator('[data-select]').count()==count
            assert page.locator('#route').input_value()==route
            page.locator('[data-layout=methods]').click()
        page.locator('[data-layout=workbench]').click()
        page.locator('#query').fill('E04')
        page.locator('#inspector summary').click()
        fields=page.locator('#inspector details dt').all_text_contents()
        record=next(r for r in exported if r['id']=='E04')
        assert fields==[k.replace('_',' ') for k in record]
        assert page.locator('#inspector details a').count()>0
        page.locator('#reset').click()
        page.locator('#assessment').select_option('apparently_suitable')
        assert page.locator('[data-select]').count()==70
        page.locator('[data-select]').nth(1).click()
        assert page.locator('#inspector h2').inner_text()==page.locator('[data-select][aria-pressed=true]').inner_text().split('\n')[0]
        page.locator('#query').fill('nothing-matches-987654')
        assert page.locator('.empty').count()==1
        page.locator('[data-layout=coverage]').click()
        page.locator('[data-route=bioconductor][data-domain=transcriptomics]').click()
        assert page.locator('#domain').input_value()=='transcriptomics'
        page.locator('[data-source]').first.click()
        assert page.locator('#detail').is_visible()
        page.locator('#closeDetail').click()
        page.locator('[data-layout=curated]').click()
        page.locator('#curatedSources').click()
        assert page.locator('[data-select]').count()==sum('raivivek/awesome-biology' in json.dumps(r) for r in exported)
        page.locator('#companionSite').click()
        page.wait_for_load_state('networkidle')
        assert page.locator('h1').inner_text()=='Analysis documents across the source inventory'
        assert page.locator('.choices [data-layout]').all_text_contents()==['Overview','Sources']
        assert 'inventory.html' in page.url
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width':1440,'height':1000})
        audit=page.evaluate('window.BIOTASKS_DATA.source_inventory')
        assert audit['all']=={'sources':1014,'located':502,'lead':2,'none_detected':509,'unknown':1}
        assert page.locator('#formatDistribution [data-format-bar]').count()==len(audit['formats'])
        for fmt in audit['formats']:
            bar=page.locator(f'[data-format-bar="{fmt}"]')
            expected=sum(fmt in r['formats'] for r in audit['rows'])
            assert int(bar.locator('strong').inner_text())==expected
        page.locator('[data-format-bar="Jupyter"]').click()
        assert page.locator('#auditRows tbody tr').count()==197
        assert page.locator('h1').inner_text()=='Explore source documents'
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width':1440,'height':1000})
        page.locator('#auditFormat').select_option('')
        assert page.locator('#auditRows tbody tr').count()==1014
        page.locator('#auditStatus').select_option('located')
        assert page.locator('#auditRows tbody tr').count()==502
        page.locator('#auditFormat').select_option('R Markdown')
        assert page.locator('#auditRows tbody tr').count()==187
        page.locator('#auditFormat').select_option('')
        page.locator('#auditStatus').select_option('')
        page.locator('#auditQuery').fill('alabaster.matrix')
        assert page.locator('#auditRows tbody tr').count()==1
        page.locator('#auditRows summary').click()
        assert 'Authoring source' in page.locator('#auditRows').inner_text()
        assert 'Extracted R code' in page.locator('#auditRows').inner_text()
        assert page.locator('#auditRows td').nth(2).locator('a').first.get_attribute('href').endswith('userguide.Rmd')
        page.locator('#auditQuery').fill('cell-eval2')
        assert page.locator('#auditRows tbody tr').count()==1
        page.locator('#auditRows summary').click()
        assert 'ArcInstitute/cell-eval' in page.locator('#auditRows').inner_text()
        page.locator('#auditQuery').fill('')
        first=next(iter(audit['domains']))
        page.locator('.choices [data-layout=repository]').click()
        assert page.locator('#auditRows').count()==0
        bars=page.locator('#domainDistribution [data-domain-bar]')
        assert bars.count()==len(audit['domains'])
        assert sum(int(v) for v in bars.locator('strong').all_text_contents())==502
        page.locator(f'[data-domain-bar="{first}"]').click()
        assert page.locator('#auditRows tbody tr').count()==audit['domains'][first]['located']
        page.locator('.choices [data-layout=repository]').click()
        page.locator('#domainChartScope').select_option('sources')
        for d,counts in audit['domains'].items():
            assert int(page.locator(f'[data-domain-bar="{d}"] strong').inner_text())==counts['sources']
        assert sum(int(v) for v in page.locator('[data-domain-bar] strong').all_text_contents())==1014
        page.locator(f'[data-domain-bar="{first}"]').click()
        assert page.locator('#auditRows tbody tr').count()==audit['domains'][first]['sources']
        guard()
        page.locator('#companionSite').click()
        page.wait_for_load_state('networkidle')
        assert page.locator('h1').inner_text()=='How we discover useful analyses'
        assert not errors,errors
    finally:
        browser.close()
print(json.dumps({'url':url,'start':started,'end':datetime.now(timezone.utc).isoformat(),'exit_status':0,'layouts':5,'checks':['methods opens first','11 route drilldowns and 4 screening steps','five views on desktop/mobile','complete JSON export equals payload','all source metadata fields rendered','source selection and filtering','coverage evidence dialog','curated index drilldown','HF collapsed by default','fixed inventory totals and format/domain filters'],'page_errors':errors,'estimated_working_set_mib':450,'max_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss},indent=2))

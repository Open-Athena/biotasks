"""Exercise the self-contained explorer using one headless browser process."""
import datetime,json,resource,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from acquire import guard
guard(True);start=datetime.datetime.now(datetime.timezone.utc).isoformat();errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/home/exedev/.local/bin/chromium',headless=True,args=['--no-sandbox','--disable-gpu','--renderer-process-limit=1','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
 url=sys.argv[1] if len(sys.argv)>1 else (ROOT/'inventory.html').as_uri()
 page.goto(url,wait_until='load',timeout=45000);page.wait_for_selector('#table tbody tr')
 assert page.title()=='BioTasks · Source classification'
 total=page.evaluate('window.biotasksExplorer.data.documents.length');assert total==4301
 assert page.evaluate('window.biotasksExplorer.getFiltered().length')==4245
 page.check('#audit');assert page.evaluate('window.biotasksExplorer.getFiltered().length')==4301
 page.uncheck('#audit')
 page.fill('#query','scvi');assert page.locator('#table tbody tr').count()>0
 page.select_option('#facet','scientific_field');page.select_option('#term','transcriptomics');assert page.locator('#table tbody tr').count()>0
 page.select_option('#review','assistant');assert page.locator('#table tbody tr').count()>0
 page.locator('details').first.click();assert page.locator('details[open] pre').first.is_visible()
 with page.expect_download() as download:page.click('#download')
 assert download.value.suggested_filename=='biotasks-documents.csv'
 page.fill('#query','');page.select_option('#term','');page.select_option('#review','')
 page.click('#repositories');assert page.locator('#table tbody tr').count()==75
 page.fill('#query','scverse/scvi-tutorials');assert page.locator('#table tbody tr').count()==1
 page.click('#vocabulary');assert page.locator('#vocab h3').count()==sum(len(page.evaluate('window.biotasksExplorer.data.vocabulary')[f]) for f in ['scientific_field','modality','operation'])
 page.click('#distributions')
 assert page.locator('#charts').is_visible()
 assert page.locator('#document-categories .bar-row').count()==20
 assert page.eval_on_selector_all('#facet-coverage .bar-row','rs=>rs.reduce((n,r)=>n+Number(r.dataset.count),0)')==4245
 assert page.eval_on_selector_all('#repo-histogram .bar-row','rs=>rs.reduce((n,r)=>n+Number(r.dataset.count),0)')==952
 assert page.eval_on_selector_all('#format-chart .bar-row','rs=>rs.reduce((n,r)=>n+Number(r.dataset.count),0)')==4245
 page.select_option('#chart-facet','modality');assert page.locator('#document-categories .bar-row').count()==31
 page.select_option('#chart-facet','operation');assert page.locator('#document-categories .bar-row').count()==30
 page.select_option('#chart-status','reviewed')
 assert page.eval_on_selector_all('#document-categories .bar-provisional',"rs=>rs.every(r=>r.style.width==='0%')")
 expected=page.locator('#document-categories .bar-row').first.get_attribute('data-count')
 page.locator('#document-categories button').first.click()
 assert page.evaluate('window.biotasksExplorer.getFiltered().length')==int(expected)
 page.select_option('#review','');page.select_option('#term','')
 page.click('#distributions');page.select_option('#chart-status','all');page.select_option('#chart-facet','scientific_field')
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
 if len(sys.argv)==1:page.screenshot(path=str(ROOT/'distributions-mobile.png'),full_page=True)
 page.set_viewport_size({'width':1440,'height':1000})
 if len(sys.argv)==1:page.screenshot(path=str(ROOT/'distributions-desktop.png'),full_page=True)
 page.click('#documents');page.fill('#query','');page.set_viewport_size({'width':390,'height':844});assert page.locator('#query').is_visible()
 if len(sys.argv)==1:page.screenshot(path=str(ROOT/'explorer-mobile.png'),full_page=False)
 page.set_viewport_size({'width':1440,'height':1000})
 if len(sys.argv)==1:page.screenshot(path=str(ROOT/'explorer-desktop.png'),full_page=False)
 browser.close()
assert not errors,errors
(ROOT/('browser-public-validation.json' if len(sys.argv)>1 else 'browser-validation.json')).write_text(json.dumps({'passed':True,'url':url,'child_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'records':total,'checks':['initial render','search','facet filter','individual review filter','evidence expansion','CSV download','repository tab','vocabulary tab','mobile and desktop rendering','distribution denominators','all three category axes','reviewed-only bars','category drilldown','responsive distribution charts'],'page_errors':errors,'python_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'estimated_combined_working_set_mib':400},indent=2)+'\n')
print('PASS: browser controls and mobile/desktop rendering.')

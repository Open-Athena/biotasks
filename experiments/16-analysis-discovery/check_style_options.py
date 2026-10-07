"""Bounded browser checks for the four presentation options."""
import json
import os
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
url = sys.argv[1] if len(sys.argv) > 1 else (root/'style-options.html').as_uri()
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
        for theme in ['editorial','atlas','console','botanical']:
            page.set_viewport_size({'width':1440,'height':1000})
            page.locator(f'[data-theme={theme}]').click()
            assert page.locator('body').get_attribute('data-style')==theme
            assert page.locator('.style-picker [aria-pressed=true]').count()==1
            page.locator('[data-tab=overview]').click()
            assert page.locator('#stats strong').all_text_contents()==['100','98','70','0']
            page.screenshot(path=f'/tmp/biotasks16-style-{theme}.png',full_page=True)
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                for view in ['overview','sources','coverage','curated','methods']:
                    page.locator(f'[data-tab={view}]').click()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(theme,width,view)
                page.locator('[data-tab=sources]').click()
                page.locator('#reset').click()
                page.locator('#assessment').select_option('apparently_suitable')
                assert page.locator('#rows .source-title').count()==70
                page.locator('#reset').click()
            guard()
        assert not errors,errors
    finally:
        browser.close()
print(json.dumps({'url':url,'start':started,'end':datetime.now(timezone.utc).isoformat(),'exit_status':0,'styles':4,'checks':['theme switching','all five views at desktop and mobile widths','100/98/70/0 counts','suitability filter'],'page_errors':errors,'estimated_working_set_mib':450,'max_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss},indent=2))

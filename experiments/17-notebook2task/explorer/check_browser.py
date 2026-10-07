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
        page.wait_for_selector('.notebook-link')
        assert page.locator('.notebook-link').count() == 14
        page.select_option('#origin', 'benchmark')
        assert page.locator('.notebook-link').count() == 2
        page.select_option('#origin', 'BixBench')
        assert page.locator('.notebook-link').count() == 1
        page.locator('.notebook-link').click()
        page.wait_for_selector('#notebook-select')
        assert page.locator('[role=tab]').all_text_contents() == ['Notebook', 'Task', 'Attempt']
        assert '/notebooks/bix-asxl1.html' in page.url
        assert page.frame_locator('#source-frame iframe').locator('section').count() == 17
        page.click('#tab-task')
        assert 'DESeq2' in page.locator('.task-instruction').inner_text()
        page.click('#tab-solution')
        assert 'No independent' in page.locator('#workspace-panel').inner_text()
        page.click('#back')
        page.wait_for_selector('.notebook-link')
        assert page.locator('#origin').input_value() == 'BixBench'
        assert page.locator('.notebook-link').count() == 1
        page.select_option('#origin', 'SETA')
        page.locator('.notebook-link').click()
        assert page.locator('#source-frame iframe').get_attribute('src') == 'https://www.kaggle.com/embed/gpreda/breast-cancer-prediction-from-cytopathology-data'
        page.select_option('#task-select', 'own')
        page.click('#tab-task')
        assert '20250607' in page.locator('.task-instruction').inner_text()
        assert page.locator('.task-instruction h1, .task-instruction h2').count() > 0
        assert page.locator('.task-instruction li').count() > 0
        assert page.locator('.task-instruction code').count() > 0
        assert page.locator('pre.task-instruction').count() == 0
        assert page.get_by_text('View Markdown source', exact=True).count() == 0
        assert page.locator('.task-card').count() == 3
        assert 'def test_' in page.locator('.verifier-code').inner_text()
        assert page.locator('.verifier-code span[style]').count() > 10
        assert page.locator('.code-surface').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(39, 40, 34)'
        assert page.locator('.artifact-scroll').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(229, 238, 248)'
        assert 'parent repair' in page.locator('.annotations').nth(1).inner_text()
        assert page.locator('.artifact-scroll').first.evaluate('(el) => el.scrollHeight > el.clientHeight')
        assert 'HistGradientBoostingClassifier' in page.locator('.solution-code').inner_text()
        assert page.locator('.solution-code span[style]').count() > 10
        page.click('#tab-solution')
        assert 'No independent LLM solver attempts' in page.locator('#workspace-panel').inner_text()
        assert page.locator('.solution-code').count() == 0
        page.click('#tab-task')
        if page.locator('#task-diagnostics').count():
            page.locator('#task-diagnostics > summary').click()
        assert page.locator('#workspace-panel tbody tr').count() == 8
        page.get_by_text('Validation evidence, repairs and limitations', exact=True).click()
        assert page.locator('.cpu-variant-validation h1').count() == 1
        assert '/validation/cpu-training-v1/native-02/' in page.locator('.cpu-variant-validation a').first.get_attribute('href')
        page.select_option('#artifact-select', 'eda.json')
        assert 'high_correlation_pairs' in page.locator('#artifact-content').inner_text()
        page.get_by_text('Authoring trace · GLM-5.3 · 12 responses', exact=True).click()
        assert 'write_file' in page.locator('#workspace-panel').inner_text()
        page.screenshot(path='/tmp/bio17-workspace-results.png', full_page=True)
        page.select_option('#task-select', 'released')
        assert page.locator('#artifact-select').count() == 0
        page.select_option('#task-select', 'glm')
        assert 'Idea-stage' in page.locator('#workspace-panel').inner_text()
        page.select_option('#task-select', 'codex')
        assert 'Draft task specification' in page.locator('#workspace-panel').inner_text()
        page.select_option('#notebook-select', 'dnase')
        page.wait_for_selector('#source-frame iframe')
        assert 'bedtools' in page.frame_locator('#source-frame iframe').locator('body').inner_text()
        page.click('#tab-task')
        assert 'Not generated' in page.locator('#detail').inner_text()
        page.click('#tab-task')
        if page.locator('#task-diagnostics').count():
            page.locator('#task-diagnostics > summary').click()
        page.click('#tab-solution')
        assert page.locator('#detail').is_hidden()
        page.click('#back')
        page.click('#reset')
        page.select_option('#group', 'gReLU')
        assert page.locator('.notebook-link').count() == 3
        with page.expect_download() as event:
            page.click('#export')
        exported = json.loads(Path(event.value.path()).read_text())
        assert len(exported['entries']) == 3
        page.fill('#search', 'zzzz-not-found')
        assert page.locator('.notebook-link').count() == 0
        assert page.locator('#empty').is_visible()
        page.click('#reset')
        page.screenshot(path='/tmp/bio17-directory.png', full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.select_option('#origin', 'SETA')
        page.locator('.notebook-link').click()
        page.select_option('#task-select', 'own')
        for tab in ['original', 'task', 'solution']:
            page.click('#tab-' + tab)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), tab
        # URL routing must preserve HTMLPreview's pinned source revision.
        routed = page.evaluate("pageURL('index.html', '#origin=SETA')")
        assert '/explorer/index.html#origin=SETA' in routed
        # Serve built files under the actual preview URL shape, without network.
        def preview_route(route):
            from urllib.parse import urlparse, unquote
            requested = urlparse(route.request.url)
            target = unquote(requested.query).split('/explorer/', 1)[-1]
            file = (root / target).resolve()
            assert file.is_relative_to(root.resolve())
            route.fulfill(path=str(file), content_type='text/html')
        page.route('https://htmlpreview.github.io/**', preview_route)
        preview = 'https://htmlpreview.github.io/?https://github.com/Open-Athena/biotasks/blob/test-revision/experiments/17-notebook2task/'
        page.goto(preview + 'explorer/index.html')
        page.select_option('#origin', 'SETA')
        page.locator('.notebook-link').click()
        page.wait_for_selector('#notebook-select')
        assert 'test-revision/experiments/17-notebook2task/explorer/notebooks/seta-cytopathology.html' in page.url
        page.click('#back')
        page.wait_for_selector('.notebook-link')
        assert page.locator('#origin').input_value() == 'SETA'
        assert not errors, errors
        print(json.dumps({'url':url,'status':'passed','entries':14,'checks':['14 unified entries','provenance and repository filters','empty search and reset','filtered export','separate detail pages','filter-preserving return navigation','17-cell offline notebook','dependent task/solution/results panels','result artifact selection','authoring timeline','390px layout','HTMLPreview URL routing'],'page_errors':errors}))
    finally:
        browser.close()

"""Browser QA. Install playwright separately; no QA dependency is needed to run the app."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', default='/Applications/Brave Browser.app/Contents/MacOS/Brave Browser')
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--screenshots', default='/private/tmp/hotspot_previews')
    parser.add_argument('--dependency-path', help='Optional directory containing Playwright')
    parser.add_argument('--preview-only', action='store_true', help='Capture fresh screenshots without running interaction checks')
    args = parser.parse_args()
    if args.dependency_path:
        sys.path.insert(0, args.dependency_path)
    from playwright.sync_api import sync_playwright, expect
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True)
        page = browser.new_page(viewport={'width': 1512, 'height': 1100}, device_scale_factor=1)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        expect(page.locator('#metric-total')).to_have_text('620')
        page.evaluate('document.fonts.ready')
        if args.preview_only:
            for name, width, height, route in [('offline-desktop',1512,1100,'offline'),('satellite-desktop',1512,1100,'api'),('offline-mobile',390,844,'offline'),('offline-tablet',1024,900,'offline')]:
                page.set_viewport_size({'width':width,'height':height})
                page.goto(args.url + '/#' + route)
                expect(page.locator('#dataset-name')).to_have_text('global_hotspots_demo.csv')
                page.evaluate('document.fonts.ready')
                page.evaluate('window.scrollTo(0,0)')
                page.wait_for_timeout(350)
                page.screenshot(path=str(output / (name + '.png')),full_page=True)
                page.screenshot(path=str(output / (name + '-viewport.png')),full_page=False)
                print(name,page.evaluate('({height:document.documentElement.scrollHeight,width:document.documentElement.scrollWidth,viewport:innerWidth,headingCount:document.querySelectorAll("#page-title").length})'))
            browser.close()
            return
        page.screenshot(path=str(output / 'offline-desktop.png'), full_page=True)
        assert page.locator('.leaflet-overlay-pane canvas').count() > 0, 'Map canvas missing'
        page.locator('#workflow-custom').click()
        page.locator('#filter-confidence').select_option('high')
        page.locator('#apply-filters').click()
        kept = int(page.locator('#metric-retained').inner_text().replace(',', ''))
        assert 0 < kept < 620
        page.locator('#table-tab').click()
        assert page.locator('#results-body tr').count() == 9
        with page.expect_download() as download:
            page.locator('#export-button').click()
        export = Path(download.value.path()).read_text(encoding='utf-8-sig')
        assert 'filter_reason' in export and 'SYNTHETIC_DEMO' in export
        page.locator('#map-tab').click()
        page.locator('#workflow-optimized').click()
        assert page.locator('#apply-filters').is_disabled(), 'Missing predictions must not fake optimized results'
        page.locator('#candidate-details').click()
        assert page.locator('#study-dialog').is_visible()
        assert '26 / 171' in page.locator('#study-dialog').inner_text()
        page.locator('#close-study').click()
        page.locator('#reset-filters').click()

        # CSV import: blanks and invalid coordinates are not silently coerced to zero.
        data = ('latitude,longitude,acq_date,acq_time,satellite,confidence,frp,retain_for_review,reason\n'
                '49.2,-123.1,2026-10-12,1300,N,h,35,True,score_keep\n'
                '0,0,2026-10-12,0300,A,20,5,False,candidate_suppress_review_required\n'
                ',11,2026-10-12,0300,T,90,20,True,score_keep\n'
                '95,22,2026-10-12,0300,T,90,20,True,score_keep\n'
                '-33,151,,,N,n,,False,insufficient_history_keep\n')
        page.locator('#file-input').set_input_files({'name':'qa.csv','mimeType':'text/csv','buffer':data.encode()})
        page.locator('#confirm-import').click()
        assert page.locator('#metric-total').inner_text() == '3'
        assert '2 rows have invalid' in page.locator('#data-notice').inner_text()
        page.locator('#workflow-optimized').click()
        page.locator('#apply-filters').click()
        assert page.locator('#metric-retained').inner_text() == '2'
        # Numeric manual filtering and missing-value policy.
        page.locator('#workflow-custom').click()
        page.locator('#filter-frp').fill('10')
        page.locator('#filter-missing').uncheck()
        page.locator('#apply-filters').click()
        assert page.locator('#metric-retained').inner_text() == '1'

        # Multiple sheets and Excel serial date conversion in the actual bundled importer.
        excel = page.evaluate("""() => {
          const wb = XLSX.utils.book_new();
          XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([['latitude','longitude','acq_date','frp'],[5,20,45943,12]]), 'First');
          XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([['Latitude','Longitude','Date','FRP'],[-12,130,'2026-10-10',50],[51,-120,'2026-10-11',15]]), 'Second');
          return XLSX.write(wb, {bookType:'xlsx', type:'base64'});
        }""")
        import base64
        page.locator('#file-input').set_input_files({'name':'qa.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':base64.b64decode(excel)})
        page.locator('#sheet-select').select_option('Second')
        page.locator('#confirm-import').click()
        assert page.locator('#metric-total').inner_text() == '2'
        assert not page.locator('#data-notice').is_visible()

        # Independent API dataset, real form validation, and mocked service response.
        page.locator('[data-page="api"]').click()
        expect(page.locator('#metric-total')).to_have_text('0')
        page.screenshot(path=str(output / 'satellite-desktop.png'), full_page=True)
        page.route('**/api/firms/query', lambda route: route.fulfill(json={'csv':'latitude,longitude,acq_date,acq_time,satellite,instrument,confidence,frp,daynight\n35,-118,2026-10-15,1305,N,VIIRS,h,12.1,D\n'}))
        page.locator('#nasa-key').fill('mock_key_for_browser_tests')
        page.locator('#nasa-area').select_option('custom')
        page.locator('#query-button').click()
        expect(page.locator('#metric-total')).to_have_text('1')
        assert 'Loaded 1 valid' in page.locator('#api-notice').inner_text()
        page.locator('[data-provider="sensenet"]').click()
        assert page.locator('#sensenet-panel').is_visible()
        assert page.locator('#sensenet-panel button').is_disabled()
        page.locator('[data-provider="nasa"]').click()

        # A configured model is not represented as a successful connection until a request.
        page.locator('#chat-settings').click()
        page.locator('#model-name').fill('qa-local-model')
        page.locator('#model-form button[type="submit"]').click()
        payloads = []
        def answer(route):
            payloads.append(route.request.post_data_json)
            route.fulfill(json={'reply':'One observation is retained. This does not establish a verified fire.'})
        page.route('**/api/chat', answer)
        page.locator('#chat-input').fill('Summarize the results')
        page.locator('#chat-send').click()
        expect(page.locator('#chat-messages')).to_contain_text('One observation is retained')
        assert payloads and 'mock_key_for_browser_tests' not in json.dumps(payloads)
        assert '"longitude"' not in json.dumps(payloads)
        page.locator('[data-page="offline"]').click()
        expect(page.locator('#metric-total')).to_have_text('2')
        assert 'One observation is retained' not in page.locator('#chat-messages').inner_text()
        page.locator('#demo-button').click()
        expect(page.locator('#metric-total')).to_have_text('620')
        page.locator('[data-page="library"]').click()
        page.locator('[data-group="optimized"]').click()
        assert page.locator('.feature-row').count() == 49
        page.screenshot(path=str(output / 'library-desktop.png'), full_page=True)
        page.locator('#feature-search').fill('stationary')
        assert page.locator('.feature-row').count() == 1
        page.locator('[data-page="guide"]').click()
        expect(page.locator('.guide-card')).to_have_count(5)
        page.locator('[data-page="offline"]').click()
        expect(page.locator('#offline-source')).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(350)
        page.screenshot(path=str(output / 'offline-mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
        page.set_viewport_size({'width':1024,'height':900})
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(350)
        page.screenshot(path=str(output / 'offline-tablet.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Tablet horizontal overflow'
        assert not errors, errors
        browser.close()
    print(json.dumps({'status':'passed','browser_errors':errors,'screenshots':str(output),'checks':['map','manual filters','optimized eligibility','conservative imported decisions','CSV validation','Excel sheets','exports','independent API state','NASA mock','LLM mock and payload privacy','feature catalogue','responsive layout']}))


if __name__ == '__main__':
    main()

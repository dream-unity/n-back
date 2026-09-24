#!/usr/bin/env python3
"""Exercise the actual standalone HTML with network access disabled.

Default: load file:// from a directory containing only the HTML.
--document-mode is for managed Chromium environments that forbid file:// URLs;
this loads the same bytes into an offline document, without relaxing policies.
Install Playwright and its Chromium browser only to run these developer tests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROBE = """
(() => {
  // Test-only observation: retain the real trainer returned by the source factory.
  let exported = {};
  const probeModule = {};
  Object.defineProperty(probeModule, 'exports', {
    get() { return exported; },
    set(value) {
      exported = value;
      if (value && typeof value.createTrainer === 'function') {
        const create = value.createTrainer;
        value.createTrainer = function(environment) {
          const instance = create(environment);
          window.__testTrainer = instance;
          return instance;
        };
      }
    }
  });
  window.module = probeModule;
})();
"""
NO_AUDIO = "Object.defineProperty(window,'AudioContext',{value:undefined,configurable:true});Object.defineProperty(window,'webkitAudioContext',{value:undefined,configurable:true});"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--html', type=Path, default=ROOT / 'Sentience-N-Back-Offline.html')
    parser.add_argument('--output', type=Path, default=ROOT / 'validation')
    parser.add_argument('--chromium', default=None)
    parser.add_argument('--document-mode', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    payload = args.html.read_bytes()
    checks, errors, network = [], [], []
    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
    with tempfile.TemporaryDirectory(prefix='sentience-n-back-isolated-') as temporary:
        isolated = Path(temporary) / 'Sentience-N-Back-Offline.html'
        isolated.write_bytes(payload)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.chromium, headless=True, args=['--no-sandbox'])
            version = browser.version
            def new_page(*, clock=False, audio=True):
                context = browser.new_context(offline=True, viewport={'width':1440,'height':1100})
                context.add_init_script(PROBE)
                if not audio:
                    context.add_init_script(NO_AUDIO)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: network.append(request.url) if request.url.startswith(('http:', 'https:', 'ws:', 'wss:')) else None)
                if clock:
                    page.clock.install()
                if args.document_mode:
                    page.evaluate(PROBE)
                    if not audio:
                        page.evaluate(NO_AUDIO)
                    page.set_content(payload.decode('utf-8'))
                else:
                    page.goto(isolated.as_uri())
                page.wait_for_function('Boolean(window.__testTrainer)')
                return context, page
            def state(page):
                return page.evaluate('window.__testTrainer.state')
            def open_training(page):
                page.locator('#open-training').click()
                page.wait_for_function('!document.getElementById("trainer").hidden')
            def answer_correctly(page):
                page.keyboard.press('j' if state(page)['current']['match'] else 'k')

            context, page = new_page(clock=True)
            check(page.locator('#training-menu').is_visible() and not page.locator('#trainer').is_visible(), 'Separate menu initially visible')
            check(page.title() == 'Sentience n-back — Dream Unity', 'Menu browser title uses Sentience n-back')
            check(page.locator('#menu-title').inner_text() == 'Sentience n-back', 'Menu heading uses Sentience n-back')
            check(page.locator('#open-training').inner_text().replace('›', '').strip() == 'Open Sentience n-back', 'Portal uses Sentience n-back')
            check(page.locator('meta[property="og:title"]').get_attribute('content') == 'Sentience n-back — Dream Unity', 'Share title uses Sentience n-back')

            page.screenshot(path=str(args.output / 'menu.png'), full_page=True)
            open_training(page)
            check(page.locator('#trainer').is_visible() and not page.locator('#training-menu').is_visible(), 'Portal opens trainer internally')
            check(page.title() == 'Sentience n-back — Dream Unity', 'Training browser title preserves branding')
            check(page.locator('#training-title').inner_text() == 'Sentience n-back', 'Training heading uses Sentience n-back')

            expected_options={'n':20,'count':3,'response':7,'session':8,'probability':6,'interference':5,'rate':7,'spacing':7,'volume':4}
            for control, count in expected_options.items():
                check(page.locator('#'+control+' option').count()==count, 'All options preserved: '+control)
            for control, value in {'n':'2','count':'3','response':'3','session':'15','probability':'35','interference':'75','rate':'average','spacing':'average','volume':'0.8'}.items():
                check(page.locator('#'+control).input_value()==value, 'Screenshot default: '+control)
            page.screenshot(path=str(args.output / 'training.png'), full_page=True)
            page.locator('#speak').uncheck()
            page.locator('#start').click()
            first = state(page)['current']['values']
            check(state(page)['score']['shown']==1 and not state(page)['current']['scored'], 'First memory-fill trial is unscored')
            check(page.locator('#match').is_disabled() and page.locator('#n').is_disabled(), 'Responses and settings locked appropriately during fill')
            page.clock.run_for(3450)
            check(state(page)['score']['shown']==2 and not state(page)['current']['scored'], 'Second 2-back fill remains unscored')
            page.clock.run_for(3450)
            check(state(page)['current']['target']==first and state(page)['awaiting'], 'First scored 2-back trial targets first sequence')
            answer_correctly(page)
            check(state(page)['score']['correct']==1 and page.locator('#feedback').inner_text()=='CORRECT', 'Keyboard answer scores correctly')
            page.keyboard.press('j')
            check(state(page)['score']['scored']==1, 'Duplicate response ignored')
            page.clock.run_for(450)
            page.keyboard.press('k' if state(page)['current']['match'] else 'j')
            check(state(page)['score']['scored']==2 and state(page)['score']['correct']==1, 'Incorrect response counted once')
            page.clock.run_for(3450)
            check(state(page)['score']['omissions']==1 and page.locator('#accuracy').inner_text()=='33%', 'Timeout penalizes accuracy')
            page.clock.run_for(450)
            page.locator('#pause').click()
            paused=state(page); paused_clock=page.locator('#clock').inner_text()
            check(paused['paused'] and page.locator('#stimulus').evaluate("e=>e.classList.contains('hidden')"), 'Pause hides sequence and blocks responses')
            page.clock.run_for(5000)
            check(state(page)['score']==paused['score'] and page.locator('#clock').inner_text()==paused_clock, 'Pause preserves trials and session clock')
            page.locator('#pause').click()
            answer_correctly(page)
            check(state(page)['score']['scored']==4 and state(page)['score']['correct']==2, 'Resume preserves current response trial')
            page.locator('#back-to-menu').click()
            page.wait_for_function('document.getElementById("trainer").hidden')
            check(not state(page)['running'] and page.locator('#training-menu').is_visible(), 'Returning to menu stops session')
            check(page.title() == 'Sentience n-back — Dream Unity', 'Returning to menu preserves branding')
            open_training(page)
            check(page.locator('#n').is_enabled() and page.locator('#start').is_enabled(), 'Controls unlocked after menu return')

            page.locator('#n').select_option('1'); page.locator('#response').select_option('1')
            page.locator('#keyboard').uncheck(); page.locator('#session').select_option('open')
            page.locator('#start').click(); page.clock.run_for(1450)
            page.keyboard.press('j')
            check(state(page)['score']['scored']==0, 'Keyboard-disabled mode ignores answer keys')
            page.locator('#match' if state(page)['current']['match'] else '#no-match').click()
            check(state(page)['score']['correct']==1, 'Pointer responses work independently of keyboard')
            page.keyboard.press('Escape')
            check(not state(page)['running'], 'Escape stops session')

            page.locator('#keyboard').check(); page.locator('#session').select_option('5')
            page.locator('#start').click(); page.clock.run_for(300100)
            check(not state(page)['running'] and page.locator('#stimulus').inner_text()=='SESSION COMPLETE', 'Timed session ends at selected duration')
            page.locator('#session').select_option('open')
            page.locator('#start').click(); page.clock.run_for(301000)
            check(state(page)['running'] and page.locator('#clock').inner_text().startswith('OPEN'), 'Open-ended session continues beyond five minutes')
            check(len(state(page)['trials'])<=8, 'Open-ended session history stays bounded')
            page.locator('#stop').click()
            page.locator('#n').select_option('20')
            page.locator('#start').click(); first=state(page)['current']['values']; page.clock.run_for(20*1450)
            check(state(page)['score']['shown']==21 and state(page)['current']['target']==first, '20-back sequence targets the correct trial')
            page.evaluate("Object.defineProperty(document,'hidden',{value:true,configurable:true}); document.dispatchEvent(new Event('visibilitychange'))")
            check(state(page)['paused'], 'Hidden-document event automatically pauses')
            page.evaluate('delete document.hidden')
            page.locator('#stop').click()
            page.set_viewport_size({'width':390,'height':844})
            check(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Trainer has no horizontal overflow at 390 pixels')
            page.screenshot(path=str(args.output / 'mobile-training.png'), full_page=True)
            page.locator('#back-to-menu').click()
            page.wait_for_function('document.getElementById("trainer").hidden')
            check(page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Menu has no horizontal overflow at 390 pixels')
            context.close()

            context, page = new_page()
            open_training(page)
            page.locator('#test').click()
            page.wait_for_function('document.getElementById("feedback").textContent === "AUDIO READY"', timeout=15000)
            check(True, 'Recorded speech completes with network disabled')
            page.locator('#n').select_option('1'); page.locator('#response').select_option('1')
            page.locator('#rate').select_option('ultra-fast'); page.locator('#spacing').select_option('ultra-fast')
            page.locator('#audio-only').check(); page.locator('#start').click()
            page.wait_for_timeout(100)
            check(state(page)['phase']=='speaking' and page.locator('#match').is_disabled(), 'Response disabled until spoken sequence completes')
            check(page.locator('#stimulus').evaluate("e=>e.classList.contains('hidden')"), 'Audio-only mode hides available spoken stimulus')
            page.locator('#pause').click(); page.wait_for_timeout(150)
            check(state(page)['paused'], 'Pause works during spoken presentation')
            page.locator('#pause').click()
            page.wait_for_function('window.__testTrainer.state.awaiting',timeout=15000)
            page.locator('#pause').click(); paused=state(page)
            page.wait_for_timeout(1300)
            check(state(page)['score']==paused['score'], 'Paused audio-only response does not time out')
            page.locator('#pause').click(); answer_correctly(page)
            check(state(page)['score']['correct']==1, 'Audio-only session accepts correct keyboard response')
            page.keyboard.press('Escape')
            page.locator('#test').click(); page.locator('#back-to-menu').click(); page.wait_for_timeout(150)
            check(not state(page)['running'] and page.locator('#training-menu').is_visible(), 'Menu safely cancels test-speech playback')
            context.close()

            context, page = new_page(audio=False)
            open_training(page)
            page.locator('#audio-only').check(); page.locator('#start').click()
            page.wait_for_function('window.__testTrainer.state.phase === "response"')
            check(not page.locator('#stimulus').evaluate("e=>e.classList.contains('hidden')"), 'Unavailable audio falls back to visible digits')
            check('Audio unavailable' in page.locator('#explanation').inner_text(), 'Unavailable-audio fallback explains the change')
            page.locator('#stop').click(); context.close()
            check(not errors, 'No JavaScript errors')
            check(not network, 'Zero HTTP, HTTPS or WebSocket requests')
            browser.close()
    report={
        'passed': True, 'browser':'Chromium '+version,
        'mode':'offline document injection' if args.document_mode else 'isolated file:// with network disabled',
        'htmlSha256':hashlib.sha256(payload).hexdigest(), 'htmlBytes':len(payload),
        'checksPassed':len(checks), 'checks':checks, 'javascriptErrors':errors, 'networkRequests':network,
        'note':'Headless browser verifies audio completion and buffers, not the physical speaker/headphone output.'
    }
    (args.output/'browser-tests.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()

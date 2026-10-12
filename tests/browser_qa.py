#!/usr/bin/env python3
"""Optional scratch QA. Requires system Playwright; never points at production.

Usage: python3 tests/browser_qa.py http://localhost:19326 <CDP websocket> <screenshots>
The first capture uses the real extension process; remaining state captures use
explicit HTTP fixtures through the real PiCode iframe/bridge and theme runtime.
"""
import base64
import json
import pathlib
import sys
import urllib.request
from playwright.sync_api import sync_playwright

base, cdp, dest = sys.argv[1:]
assert base.startswith('http://localhost:'), 'Scratch localhost only'
out = pathlib.Path(dest); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/'server'))
from catalog import public_catalog

rows = [dict(a, installed=True, state='ready') for a in public_catalog()]
mode = 'real'
pending = []
ws_error = False
workspace_kind = "normal"
snapshot_error = False
status_error = False
native_preview = pathlib.Path('/mnt/e/picode-qa-office-20261012/wordcraft-preview.png')
preview = base64.b64encode(native_preview.read_bytes()).decode() if native_preview.exists() else ''

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(cdp)
    context = browser.new_context(viewport={'width':1440,'height':1000}, color_scheme='dark')
    page = context.new_page()
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    def reply(route, status, data): route.fulfill(json={'status':status,'body':json.dumps(data)})
    def route_process(route):
        req = route.request.post_data_json; path = req.get('path')
        # HTTP fixtures are explicit; live /catalog is always used.
        if mode == 'real' or path == '/catalog': route.continue_(); return
        if mode == 'blocked': reply(route,503,{'message':'The extension is off.'}); return
        if path == '/workspaces': reply(route,500,{'message':'QA workspace error'}) if ws_error else reply(route,200,{'workspaces':[] if workspace_kind=='empty' else [{'id':'qa','name':'QA project','path':'' if workspace_kind=='no-folder' else '/qa/project'}]}); return
        if path == '/status':
            if mode == 'loading': pending.append(route); return
            reply(route,500,{'message':'QA status unavailable. Try again.'}) if status_error else reply(route,200,{'apps':rows}); return
        if path in ['/open','/open-file']: pending.append(route); return
        if path == '/snapshot':
            if snapshot_error: reply(route,409,{'message':'Preview unavailable. Try again.'})
            else: reply(route,200,{'image':preview,'mime':'image/png','caption':'Rendered document page · QA fixture'})
            return
        reply(route,200,{'message':'Opened QA file.'})
    page.route('**/api/extensions/artcraft/frame/process', route_process)
    url = base + '/desktop/#/app/ext%2Fartcraft%2Fapps'
    def go():
        page.goto(url) if page.url != url else page.reload(); frame = page.frame_locator('iframe[title="Crafting Apps"]')
        frame.locator('#search').wait_for(); return frame
    def capture(name):
        page.screenshot(path=str(out/('craftapps-'+name+'.png')))
    def check_geometry(frame):
        result = frame.locator('body').evaluate('''() => {
          const bad=[];
          for (const row of document.querySelectorAll('[data-align-row]')) {
            const rects=[...row.children].filter(e=>e.getClientRects().length).map(e=>e.getBoundingClientRect());
            if(rects.some(r=>Math.abs(r.height-rects[0].height)>1 || Math.abs(r.top-rects[0].top)>1))bad.push(row.className);
          }
          return {outerOverflow:document.documentElement.scrollWidth>innerWidth,outerVertical:document.documentElement.scrollHeight>innerHeight+1,bad};
        }''')
        assert not result['outerOverflow'] and not result['outerVertical'] and not result['bad'], result
    frame = go(); frame.locator('#freshness').get_by_text('Checked just now').wait_for(timeout=60000)
    assert frame.locator('.app-row').count()==10
    capture('real-desktop'); check_geometry(frame)
    frame.locator('#catalog').evaluate('(e)=>e.scrollTop=e.scrollHeight')
    assert frame.locator('[data-app="filmcraft"]').evaluate('(e)=>{const r=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect();return r.top>=p.top&&r.bottom<=p.bottom}')
    capture('real-list-bottom')
    mode = 'loading'; frame = go(); frame.locator('.app-row').first.wait_for(); capture('loading-fixture')
    mode = 'fixture'
    for r in pending: reply(r,200,{'apps':rows})
    pending.clear(); frame.locator('#freshness').get_by_text('Checked just now').wait_for()
    frame.get_by_role('button',name='Open WordCraft',exact=True).click()
    frame.get_by_text('Opening WordCraft…',exact=True).wait_for(); capture('opening-fixture')
    for _ in range(20):
        if pending: break
        page.wait_for_timeout(50)
    assert pending, 'Open request did not reach the host bridge'
    rows[0].update(state='connected',open=True,openedForRoot='/qa/project')
    for r in pending: reply(r,200,{'message':'Opened WordCraft.'})
    pending.clear(); page.wait_for_timeout(100); frame.get_by_role('button',name='Show preview',exact=True).wait_for(timeout=5000); frame.get_by_role('button',name='Show preview',exact=True).click()
    frame.locator('.preview img').wait_for(); capture('connected-preview-fixture')
    snapshot_error=True
    frame.get_by_role('button',name='Refresh preview').click(); frame.get_by_text('Preview unavailable. Try again.',exact=True).wait_for()
    assert frame.locator('.preview img').count()==1; capture('preview-error-fixture'); snapshot_error=False
    frame.locator('#search').fill('nothing matches this search'); assert frame.locator('.app-row').count()==0
    frame.get_by_role('button',name='Clear filters').wait_for(); capture('empty-search-fixture'); frame.get_by_role('button',name='Clear filters').click()
    frame.locator('#category').select_option('Documents'); assert frame.locator('.app-row').count()==5
    frame.locator('#category').select_option('All')
    frame.locator('[data-app="gridcraft"]').focus(); frame.locator('[data-app="gridcraft"]').press('Enter'); assert frame.locator('#detail h2').inner_text()=='GridCraft'
    page.evaluate('''() => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/host-context-changed',params:{context:{path:'/qa/project/office-acceptance.docx',workspaceId:'qa'}}},'*')''')
    frame.get_by_role('button',name='Open in WordCraft',exact=True).wait_for(); frame.locator('#file-action').click(); capture('file-opening-fixture'); assert frame.locator('#file-action').is_disabled()
    frame.locator('#refresh').click(); frame.locator('#freshness').get_by_text('Checked just now').wait_for(); assert frame.locator('#file-action').is_disabled()
    for _ in range(20):
        if pending: break
        page.wait_for_timeout(50)
    assert pending, 'File open did not reach the host bridge'
    for r in pending: reply(r,200,{'message':'Opened QA file.'})
    pending.clear(); frame.get_by_text('Opened QA file.',exact=True).wait_for(); capture('file-opened-fixture')
    page.evaluate('''() => document.querySelector('iframe').contentWindow.postMessage({jsonrpc:'2.0',method:'ui/notifications/host-context-changed',params:{context:null}},'*')''')
    rows[0].update(state='uncontrolled',open=False); frame.locator('#refresh').click(); frame.locator('[data-app="wordcraft"]').click()
    frame.get_by_text('Open without an agent connection',exact=True).wait_for(); capture('uncontrolled-fixture')
    rows[0].update(state='connected',open=True,openedForRoot='/other'); frame.locator('#refresh').click()
    frame.get_by_text('Opened for another workspace',exact=True).wait_for(); capture('workspace-mismatch-fixture')
    rows[0].update(state='ready',open=False,openedForRoot=None)
    workspace_kind='empty'; frame=go(); frame.get_by_text('Enable Crafting Apps in a workspace to open apps.',exact=True).wait_for(); capture('empty-workspace-fixture'); assert frame.get_by_role('button',name='Open WordCraft',exact=True).is_disabled()
    workspace_kind='no-folder'; frame=go(); frame.get_by_text('This workspace has no folder. Choose a workspace with a folder.',exact=True).wait_for(); capture('no-folder-fixture'); assert frame.get_by_role('button',name='Open WordCraft',exact=True).is_disabled()
    workspace_kind='normal'
    ws_error=True; frame=go(); frame.get_by_text('Could not load workspaces. Try again.',exact=True).wait_for(); capture('workspace-error-fixture')
    ws_error=False; frame.locator('#retry').click(); frame.locator('#problem').wait_for(state='hidden')
    status_error=True; frame.locator('#refresh').click(); frame.get_by_text('QA status unavailable. Try again.',exact=True).wait_for(); assert frame.locator('.app-row').count()==10; capture('status-error-fixture'); status_error=False
    # Missing-process fixture through the existing host relay, with the real catalog.
    mode='blocked'; frame=go(); frame.get_by_text('Enable Crafting Apps in a workspace to use this page.',exact=True).wait_for(); capture('blocked-fixture')
    mode='fixture'; rows[0].update(state='ready',open=False,openedForRoot=None); frame=go(); frame.locator('#freshness').get_by_text('Checked just now').wait_for()
    page.locator('button[aria-label="Actions for Crafting Apps"]').click()
    page.wait_for_timeout(250)
    audit=page.evaluate('window.__picodeOverlayAudit()'); assert audit['ok'], audit
    capture('host-menu-fixture'); page.keyboard.press('Escape')
    primary=frame.get_by_role('button',name='Open WordCraft',exact=True); before=primary.evaluate('(e)=>getComputedStyle(e).filter'); primary.hover(); after=primary.evaluate('(e)=>getComputedStyle(e).filter'); assert before!=after; capture('hover-fixture')
    page.evaluate('document.documentElement.dataset.theme="light"'); page.wait_for_timeout(300); capture('light-fixture'); check_geometry(frame)
    page.evaluate('document.documentElement.dataset.theme="dark"')
    page.set_viewport_size({'width':650,'height':850}); frame.locator('[data-app="wordcraft"]').click(); capture('narrow-detail-fixture'); check_geometry(frame)
    frame.get_by_role('button',name='← All apps').click(); capture('narrow-list-fixture')
    page.goto(base+'/mobile/?mobile=1#/extensions/artcraft/pages/apps'); page.set_viewport_size({'width':390,'height':844})
    frame=page.frame_locator('iframe[title="Crafting Apps"]'); frame.locator('#search').wait_for(); frame.locator('#freshness').get_by_text('Checked just now').wait_for()
    frame.locator('[data-app="wordcraft"]').click(); capture('mobile-detail-fixture'); check_geometry(frame)
    frame.get_by_role('button',name='← All apps').click(); capture('mobile-list-fixture'); check_geometry(frame)
    assert not errors, errors
    print(json.dumps({'browser':'PASS','hostOverlayAudit':audit,'screenshots':str(out),'stateFixtures':True,'errors':errors},indent=2))
    context.close()

from playwright.sync_api import sync_playwright
import json, time

errors=[]; failed=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('requestfailed', lambda r: failed.append((r.url, r.failure)))
    page.goto('http://127.0.0.1:8080/', wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(2500)
    print('TITLE:',page.title())
    print('URL:',page.url)
    # count rendered site icons
    print('IMG count:', page.locator('img').count())
    print('visible text sample:', repr(page.locator('body').inner_text()[:400]))
    # check background image computed style
    bg=page.evaluate("getComputedStyle(document.body).backgroundImage")
    print('BODY BG:',bg[:200])
    print('PAGE ERRORS:',len(errors))
    for e in errors[:10]: print('  ERR:',e[:200])
    # filter failed local requests only
    lf=[f for f in failed if '127.0.0.1' in f[0]]
    print('FAILED LOCAL REQUESTS:',len(lf))
    for f in lf[:15]: print('  FAILED:',f[0],f[1])
    page.screenshot(path='preview.png', full_page=True)
    browser.close()

from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1000)
    def names(): return pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].map(e=>e.title).filter(Boolean)""")
    print('before toggle:',len(names()),names()[:4])

    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(1000)
    ns=names(); btxt=pg.evaluate("document.body.innerText")
    print('after toggle (外网):',len(ns),ns[:6])
    print('  has Youtube/Facebook:',('Youtube' in btxt, 'Facebook' in btxt))
    outer=pg.evaluate("""() => [...document.querySelectorAll('.navi-btn-item')].filter(e=>e.offsetWidth>0).map(e=>e.title)""")
    print('  visible tabs:',outer)
    if '综合' in outer:
        pg.locator('.navi-btn-item[title="综合"]').click(force=True)
        pg.wait_for_timeout(700)
        ns=names()
        print('  综合:',len(ns),ns[:5])

    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(900)
    print('after toggle back:',len(names()),names()[:4])

    print('ERRORS:',len(errors),'FAILED:',len(failed))
    for e in errors[:3]: print(' ',e[:150])
    for f in failed[:3]: print(' ',f[0][:100],f[1])
    pg.screenshot(path='preview_fixed.png',full_page=True)
    b.close()

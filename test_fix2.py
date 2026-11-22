from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1000)

    def links():
        return pg.evaluate("""() => [...document.querySelectorAll('.web-site-item-title')].map(e=>e.textContent.trim()).filter(Boolean)""")

    def bodytxt(): return pg.evaluate("document.body.innerText")

    # TEST tabs - check title attribute highlights + content
    for tab,expect in [('生活','房天下'),('产品','^'),('设计','^'),('运营','^'),('金融','^'),('大学','^')]:
        el=pg.locator(f'.navi-btn-item[title="{tab}"]')
        el.click(force=True)
        pg.wait_for_timeout(800)
        btxt=bodytxt()
        names=links()
        cls=el.get_attribute('class')
        print(f'tab {tab:<4} selected={"current" in cls} links={len(names)} first5={names[:5]}')

    # TEST toggle to outer
    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(1000)
    btxt=bodytxt()
    print('\nToggle -> OUTER:')
    print('  has Youtube:', 'Youtube' in btxt, '| Facebook:', 'Facebook' in btxt)
    names=links()
    print('  links:',len(names),names[:6])

    # click 综合 outer category
    pg.locator('.navi-btn-item[title="综合"]').click(force=True)
    pg.wait_for_timeout(800)
    btxt=bodytxt()
    print('  综合 tab: Yahoo:', 'Yahoo' in btxt, '| Pinterest:', 'Pinterest' in btxt)

    # toggle back to inner
    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(800)
    print('\nToggle back -> INNER: has bilibili:', 'bilibili' in bodytxt())

    print('\nERRORS:',len(errors)); [print(' ',e[:150]) for e in errors[:5]]
    print('FAILED:',len(failed)); [print(' ',f) for f in failed[:5]]
    pg.screenshot(path='preview_fixed.png',full_page=True)
    b.close()

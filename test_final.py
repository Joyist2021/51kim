from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1000)

    def names():
        return pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].map(e=>e.title).filter(Boolean)""")

    print('=== 分类标签测试 ===')
    for tab,expect in [('生活','房天下'),('产品','^'),('设计','^'),('运营','^'),('金融','^')]:
        pg.locator(f'.navi-btn-item[title="{tab}"]').click(force=True)
        pg.wait_for_timeout(700)
        ns=names()
        print(f'  {tab:<4}: {len(ns)} sites, first={ns[:4]}')

    print('\n=== 绿色开关测试（内网/外网切换）===')
    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(900)
    ns=names()
    btxt=pg.evaluate("document.body.innerText")
    print(f'  外网模式: {len(ns)} sites, first={ns[:6]}')
    print('  含 Youtube:', 'Youtube' in btxt)
    # outer category tabs
    outer=pg.evaluate("""() => [...document.querySelectorAll('.navi-btn-item')].filter(e=>e.offsetWidth>0).map(e=>e.title)""")
    print('  可见分类:',outer)
    if '综合' in outer:
        pg.locator('.navi-btn-item[title="综合"]').click(force=True)
        pg.wait_for_timeout(700)
        ns=names()
        print(f'  综合分类: {len(ns)} sites, first={ns[:5]}')

    # toggle back
    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(900)
    ns=names()
    print(f'  切回内网: {len(ns)} sites, first={ns[:4]}')

    print('\nERRORS:',len(errors)); [print(' ',e[:150]) for e in errors[:5]]
    print('FAILED:',len(failed)); [print(' ',f) for f in failed[:5]]
    pg.screenshot(path='preview_fixed.png',full_page=True)
    b.close()

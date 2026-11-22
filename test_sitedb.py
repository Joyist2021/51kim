from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1000)
    print('TITLE:',pg.title())
    # header icons (arrow 2)
    icons=pg.evaluate("""() => [...document.querySelectorAll('.head-nav-item-img')].filter(e=>e.offsetWidth>0).map(e=>e.title)""")
    print('header icons visible:',icons)
    # default sites (arrow 1)
    sites=pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].filter(e=>e.offsetWidth>0).map(e=>e.title).filter(Boolean)""")
    print('default sites:',len(sites),sites[:5])
    # switch categories - all inner
    for tab in ['生活','职能','设计','产品','运营']:
        pg.locator(f'.navi-btn-item[title="{tab}"]').click(force=True)
        pg.wait_for_timeout(600)
        n=pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].filter(e=>e.offsetWidth>0).length""")
        print(f'  {tab}: {n} sites')
    # toggle outer
    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(900)
    n=pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].filter(e=>e.offsetWidth>0).length""")
    print('outer mode sites:',n)
    print('\nERRORS:',len(errors)); [print('  ',e[:150]) for e in errors[:5]]
    localfail=[f for f in failed if '127.0.0.1' in f[0]]
    print('FAILED local:',len(localfail)); [print('  ',f[0][-70:]) for f in localfail[:5]]
    pg.screenshot(path='preview_sitedb.png',full_page=True)
    b.close()

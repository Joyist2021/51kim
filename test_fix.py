from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1200)

    def site_names():
        return pg.evaluate("""() => [...document.querySelectorAll('.web-site-item-title, [class*=site-item] span, .site-item-name')].map(e=>e.textContent.trim()).filter(Boolean).slice(0,15)""")

    # TEST 1: category tabs
    for tab in ['生活','产品','设计','金融','大学']:
        pg.locator(f'.navi-btn-item[title="{tab}"]').click()
        pg.wait_for_timeout(700)
        txt=pg.evaluate("document.body.innerText")
        # count site links visible
        n=pg.evaluate("""() => [...document.querySelectorAll('a')].filter(a=>a.offsetWidth>0&&a.href&&a.href.startsWith('http')&&!a.href.includes('127.0.0.1')).length""")
        print(f'tab {tab}: visible external links={n}, body has {tab} content? groups sample:', repr(txt[txt.find('常用')+10:txt.find('常用')+60]))

    # TEST 2: green toggle (外网)
    pg.locator('.toggle-btn').click()
    pg.wait_for_timeout(1000)
    txt=pg.evaluate("document.body.innerText")
    print('\nAfter toggle to OUTER:')
    print('  contains Youtube:', 'Youtube' in txt)
    print('  contains Facebook:', 'Facebook' in txt)
    print('  search logo alt:', pg.evaluate("""() => {const i=document.querySelector('img[src*=google]'); return i?i.alt:'no-google-img'}"""))
    # click an outer category
    pg.locator('.navi-btn-item[title="综合"]').click()
    pg.wait_for_timeout(700)
    txt2=pg.evaluate("document.body.innerText")
    print('  after 综合 tab, has Yahoo:', 'Yahoo' in txt2, ' Pinterest:', 'Pinterest' in txt2)

    print('\nERRORS:',len(errors)); [print(' ',e[:200]) for e in errors[:5]]
    print('FAILED:',len(failed)); [print(' ',f) for f in failed[:5]]
    b.close()

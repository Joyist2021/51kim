from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(900)
    def names(): return pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].filter(e=>e.offsetWidth>0&&e.title&&e.title.trim()).map(e=>e.title)""")
    print('=== SQLite 站点数据验证 ===')
    print('常用:',len(names()),names()[:4])
    for tab in ['生活','设计','运营']:
        pg.locator(f'.navi-btn-item[title="{tab}"]').click(force=True); pg.wait_for_timeout(600)
        print(f'{tab}:',len(names()),names()[:3])
    print('\n=== 右上角图标 ===')
    icons=pg.evaluate("""() => [...document.querySelectorAll('.head-nav-item-img')].filter(e=>e.offsetWidth>0).map(e=>e.title)""")
    print(icons)
    # verify each header icon still opens its panel
    pg.locator('.user-center-icon').click(force=True); pg.wait_for_timeout(400)
    print('个人中心 panel:',pg.evaluate("document.querySelector('.la-overlay').classList.contains('la-open')"))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    pg.locator('.bg-center-icon').click(force=True); pg.wait_for_timeout(900)
    print('壁纸中心 imgs:',pg.evaluate("""() => document.querySelectorAll('.setting.bgcenter img').length"""))
    print('\nERRORS:',len(errors),'FAILED local:',len([f for f in failed if '127.0.0.1' in f[0]]))
    for e in errors[:3]: print('  ',e[:120])
    pg.screenshot(path='preview_sitedb_final.png')
    b.close()

from playwright.sync_api import sync_playwright
errors=[]; failed=[]; console=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('console',lambda m: console.append((m.type,m.text)) if m.type in ('error','warning') else None)
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1500)

    # find tab elements
    tabs=pg.locator('text=生活')
    print('生活 locators:',tabs.count())
    for i in range(tabs.count()):
        el=tabs.nth(i)
        print('  ',i,'tag=',el.evaluate('e=>e.tagName'),'class=',el.get_attribute('class'),'visible=',el.is_visible())

    print('\n--- click 生活 ---')
    before=pg.locator('body').inner_text()[:300]
    tabs.first.click()
    pg.wait_for_timeout(1200)
    after=pg.locator('body').inner_text()[:300]
    print('content changed?', before!=after)
    print('after:',repr(after[:200]))
    print('errors after tab:',len(errors))
    for e in errors[:5]: print('  ',e[:300])

    # find green toggle
    print('\n--- toggle candidates ---')
    toggles=pg.locator('[class*=switch],[class*=toggle],[class*=flower]')
    for i in range(min(toggles.count(),20)):
        el=toggles.nth(i)
        print('  ',i,'class=',el.get_attribute('class'),'tag=',el.evaluate('e=>e.tagName'),'visible=',el.is_visible())

    print('\n--- page errors total ---',len(errors))
    for e in errors[:10]: print('  ERR:',e[:300])
    print('--- console errors ---',len(console))
    for c in console[:10]: print('  ',c[0],c[1][:250])
    print('--- failed requests ---',len(failed))
    for f in failed[:10]: print('  ',f[0][:150],f[1])
    b.close()

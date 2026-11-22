from playwright.sync_api import sync_playwright
reqs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.on('request',lambda r: reqs.append(r.url) if 'bgimg/get_list' in r.url else None)
    pg.goto('https://www.51kim.com/',wait_until='domcontentloaded',timeout=30000)
    pg.wait_for_timeout(2500)
    pg.locator('.bg-center-icon').first.locator('xpath=..').click(force=True)
    pg.wait_for_timeout(1500)
    # get all category tab titles
    tabs=pg.evaluate("""() => [...document.querySelectorAll('.setting.bgcenter .navi-btn-item, .setting .navi-btn-item')].filter(e=>e.offsetWidth>0).map(e=>e.title||e.textContent.trim())""")
    print('tabs:',tabs)
    mapping={}
    for t in tabs:
        reqs.clear()
        try:
            pg.locator(f'.navi-btn-item[title="{t}"]').last.click(force=True,timeout=3000)
            pg.wait_for_timeout(1200)
            ids=[u.split('classId=')[1].split('&')[0] for u in reqs if 'classId=' in u]
            mapping[t]=ids[-1] if ids else None
        except Exception as e:
            mapping[t]='ERR'
    print('\n=== category -> classId ===')
    for t,i in mapping.items(): print(f'  {t}: {i}')
    b.close()

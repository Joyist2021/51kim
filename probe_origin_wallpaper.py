from playwright.sync_api import sync_playwright
reqs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.on('request',lambda r: reqs.append((r.method,r.url)) if ('bgimg' in r.url or 'bgclass' in r.url or '/front/' in r.url) else None)
    try:
        pg.goto('https://www.51kim.com/',wait_until='domcontentloaded',timeout=30000)
        pg.wait_for_timeout(3000)
        print('title:',pg.title())
        # open wallpaper center
        for sel in ['.bg-center-icon','[class*=bg-center]','[class*=wallpaper]']:
            try:
                el=pg.locator(sel).first
                if el.count() and el.is_visible():
                    el.locator('xpath=..').click(force=True); print('clicked',sel); break
            except Exception: pass
        pg.wait_for_timeout(2000)
        print('requests after open:',[u.split('51kim.com')[-1] for _,u in reqs])
        reqs.clear()
        # click 风景
        pg.locator('.navi-btn-item[title="风景"]').first.click(force=True)
        pg.wait_for_timeout(2500)
        print('requests after 风景:',[u.split('51kim.com')[-1] for _,u in reqs])
        # response body
        body=pg.evaluate("document.body.innerText")
        print('has wallpaper content:', len(body))
    except Exception as e:
        print('ERR:',str(e)[:200])
    b.close()

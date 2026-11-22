from playwright.sync_api import sync_playwright
errors=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(800)
    print('TITLE:',pg.title())
    print('fresh DB - auth/me:',pg.evaluate("""async()=>{const r=await fetch('/auth/me');return (await r.json())}"""))

    # arrow1: login panel
    pg.locator('.user-center-icon').click(force=True); pg.wait_for_timeout(300)
    print('arrow1 login panel:',pg.evaluate("document.querySelector('.la-overlay').classList.contains('la-open')"))
    pg.keyboard.press('Escape')

    # arrow2: wallpaper
    pg.locator('.bg-center-icon').click(force=True); pg.wait_for_timeout(900)
    wp=pg.evaluate("""()=>{const p=document.querySelector('.setting.bgcenter');return p?{imgs:p.querySelectorAll('img').length,tabs:p.querySelectorAll('.navi-btn-item').length}:null}""")
    print('arrow2 wallpaper:',wp)
    pg.keyboard.press('Escape')

    # arrow3: share
    pg.locator('.share-icon').click(force=True); pg.wait_for_timeout(900)
    sh=pg.evaluate("""()=>{const p=[...document.querySelectorAll('.setting')].find(x=>x.innerText.includes('告诉朋友'));return p?p.innerText.slice(0,60):'none'}""")
    print('arrow3 share:',repr(sh))

    print('ERRORS:',len(errors),'FAILED:',len(failed))
    for e in errors[:3]: print(' ',e[:120])
    b.close()

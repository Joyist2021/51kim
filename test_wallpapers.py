from playwright.sync_api import sync_playwright
errors=[]; failed=[]
CATS={'动态':'10','风景':'2','素雅':'4','唯美':'5','纯色':'6','静物':'7','星空':'8','城市':'9','人物':'11'}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.on('requestfailed',lambda r: failed.append((r.url,r.failure)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(700)
    pg.locator('.bg-center-icon').click(force=True)
    pg.wait_for_timeout(1200)
    for name,cid in CATS.items():
        pg.locator(f'.navi-btn-item[title="{name}"]').last.click(force=True)
        pg.wait_for_timeout(1000)
        # count loaded wallpaper images in panel
        stats=pg.evaluate("""() => {
          const p=[...document.querySelectorAll('.setting')].find(x=>x.offsetWidth>0 && x.querySelectorAll('.bg-list-item, [class*=bg-item]').length);
          const imgs=[...document.querySelectorAll('.setting img')].filter(i=>i.offsetWidth>0);
          const ok=imgs.filter(i=>i.complete && i.naturalWidth>0).length;
          return {total:imgs.length, ok:ok};
        }""")
        print(f'  {name}(id={cid}): visible imgs {stats["ok"]}/{stats["total"]}')
    print('\nERRORS:',len(errors)); [print('  ',e[:130]) for e in errors[:4]]
    localfail=[f for f in failed if '127.0.0.1' in f[0]]
    print('FAILED local:',len(localfail)); [print('  ',f[0][-70:]) for f in localfail[:6]]
    pg.screenshot(path='wallpaper_all.png')
    b.close()

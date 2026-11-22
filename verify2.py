from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1440,'height':900})
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1500)
    # check all background-image URLs resolve (sample 8)
    urls=pg.evaluate("""() => {
      const out=[];
      document.querySelectorAll('*').forEach(el=>{
        const bg=getComputedStyle(el).backgroundImage;
        const m=bg&&bg.match(/url\\(["']?([^"')]+)["']?\\)/);
        if(m&&m[1].includes('127.0.0.1')) out.push(m[1]);
      });
      return [...new Set(out)];
    }""")
    print('local bg images used:',len(urls))
    # test them via JS fetch status
    bad=pg.evaluate("""async (urls) => {
      const bad=[];
      for(const u of urls.slice(0,40)){
        try{const r=await fetch(u,{method:'HEAD'}); if(!r.ok) bad.push([u,r.status]);}
        catch(e){bad.push([u,String(e)]);}
      }
      return bad;
    }""", urls)
    print('broken bg images:',len(bad)); [print(' ',x) for x in bad[:10]]
    # tab switching
    tabs=pg.locator('text=生活').first
    if tabs.count():
        tabs.click(); pg.wait_for_timeout(500)
        print('after clicking 生活 tab, body text has 常用:', '常用' in pg.locator('body').inner_text()[:200])
    # check search form action
    form=pg.locator('form').first
    if form.count(): print('search form action:',form.get_attribute('action'))
    b.close()

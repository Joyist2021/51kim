from playwright.sync_api import sync_playwright
reqs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1080,'height':640})
    pg.on('request',lambda r: reqs.append(r.url) if '/front/' in r.url else None)
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(1200)

    # inspect the tab structure
    info=pg.evaluate("""() => {
      const el=[...document.querySelectorAll('span')].find(x=>x.textContent.trim()==='生活');
      if(!el) return null;
      let p=el, chain=[];
      for(let i=0;i<4&&p;i++,p=p.parentElement){
        chain.push({tag:p.tagName,cls:p.className,id:p.id,outer:p.outerHTML.slice(0,500)});
      }
      return chain;
    }""")
    print('=== 生活 element chain ===')
    for c in info or []: print(c)

    # look at site group tab container classes
    print('\n=== all elements whose text is a tab name ===')
    print(pg.evaluate("""() => [...document.querySelectorAll('*')].filter(e=>['常用','生活','职能','设计','产品','运营'].includes(e.textContent.trim())&&e.children.length===0).map(e=>({tag:e.tagName,cls:e.className,par:e.parentElement.className})).slice(0,20)"""))

    reqs.clear()
    print('\n=== click 生活, capture requests + full text hash ===')
    before=pg.evaluate("document.body.innerText")
    pg.locator('text=生活').first.click()
    pg.wait_for_timeout(1500)
    after=pg.evaluate("document.body.innerText")
    print('text len before/after:',len(before),len(after),'identical:',before==after)
    print('requests after click:')
    for r in reqs: print('  ',r)

    # check which tab has active class
    print('\n=== tab active states after click ===')
    print(pg.evaluate("""() => [...document.querySelectorAll('*')].filter(e=>['常用','生活','职能','设计','产品','运营'].includes(e.textContent.trim())&&e.children.length===0).map(e=>({t:e.textContent.trim(),cls:e.className,parCls:e.parentElement.className}))"""))

    # toggle: inspect and click
    print('\n=== inspect toggle-btn ===')
    tg=pg.evaluate("""() => {const e=document.querySelector('.toggle-btn'); return e?{outer:e.outerHTML,parent:e.parentElement.outerHTML.slice(0,800)}:null}""")
    print(tg)
    reqs.clear()
    pg.locator('.toggle-btn').click(force=True)
    pg.wait_for_timeout(1200)
    print('requests after toggle:',reqs)
    print('any new visible panel? body text tail:',repr(pg.evaluate("document.body.innerText")[-300:]))
    b.close()

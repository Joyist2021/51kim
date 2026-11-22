from playwright.sync_api import sync_playwright
reqs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.on('request',lambda r: reqs.append(r.url) if '/front/site/get_list' in r.url else None)
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(800)
    print('initial sites:',pg.evaluate("""() => [...document.querySelectorAll('a.web-group-item')].filter(e=>e.offsetWidth>0).length"""))
    reqs.clear()
    pg.locator('.navi-btn-item[title="生活"]').click(force=True)
    pg.wait_for_timeout(1000)
    print('requests:',[u.split('8080')[-1] for u in reqs])
    # count per visible container
    info=pg.evaluate("""() => {
      const out=[];
      document.querySelectorAll('a.web-group-item').forEach(a=>{
        if(a.offsetWidth>0){
          let p=a, cls='';
          for(let i=0;i<4&&p;i++,p=p.parentElement){ if(p.className && String(p.className).includes('group')) cls=String(p.className); }
          out.push({t:a.title,cls:cls.slice(0,40)});
        }
      });
      return out;
    }""")
    print('visible site count:',len(info))
    print('first 10:',[x['t'] for x in info[:10]])
    # check if 房天下 present (生活 category signature)
    body=pg.evaluate("document.body.innerText")
    print('has 房天下:', '房天下' in body, '| has bilibili:', 'bilibili' in body)
    b.close()

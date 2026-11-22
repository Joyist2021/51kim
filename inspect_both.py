from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    pg=b.new_page(viewport={'width':1280,'height':800})
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(800)
    # right-top 4 icons
    info=pg.evaluate("""() => {
      const out=[];
      document.querySelectorAll('*').forEach(e=>{
        const r=e.getBoundingClientRect();
        if(r.top>=0&&r.top<45&&r.right>1150&&r.width>8&&r.width<35&&r.height>8&&r.height<35){
          const s=getComputedStyle(e);
          if(s.cursor==='pointer'||e.tagName==='A'||e.onclick){
            out.push({tag:e.tagName,cls:String(e.className).slice(0,60),title:e.title||'',id:e.id,
                      bg:s.backgroundImage.slice(0,90),x:Math.round(r.x),w:Math.round(r.width)});
          }
        }
      });
      return out.sort((a,b)=>a.x-b.x);
    }""")
    print('=== right-top icons ===')
    for o in info: print(o)
    b.close()

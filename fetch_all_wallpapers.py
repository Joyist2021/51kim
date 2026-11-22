import urllib.request, json, re, os, concurrent.futures
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Referer':'https://www.51kim.com/'}
BASE='https://www.51kim.com'
CATS={'10':'动态','2':'风景','4':'素雅','5':'唯美','6':'纯色','7':'静物','8':'星空','9':'城市','11':'人物'}

def fetch(kv):
    cid,name=kv
    data=urllib.request.urlopen(urllib.request.Request(f'{BASE}/front/bgimg/get_list?classId={cid}&curReqMark=0',headers=UA),timeout=25).read()
    open(f'api/bgimg_{cid}.json','wb').write(data)
    obj=json.loads(data)
    return cid,name,len(obj.get('responseBody','') or '')

results=[]
for kv in CATS.items():
    try: results.append(fetch(kv))
    except Exception as e: print('FAIL',kv[0],str(e)[:60])
for cid,name,bl in sorted(results,key=lambda x:int(x[0])):
    print(f'  classId={cid:>3} {name}: body {bl} chars')

# collect all image resource paths from all wallpaper data
paths=set()
for cid in CATS:
    try:
        obj=json.load(open(f'api/bgimg_{cid}.json',encoding='utf-8'))
        body=obj.get('responseBody','') or ''
        paths|=set(re.findall(r'kimzhuye/[\w/.-]+?\.(?:png|jpg|jpeg|gif|html|htm)',body))
    except Exception: pass
print(f'\nTotal unique wallpaper resources: {len(paths)}')

missing=[p for p in sorted(paths) if not os.path.exists(os.path.join('res',p.replace('/',os.sep)))]
print('Missing locally:',len(missing))

def dl(p):
    dest=os.path.join('res',p.replace('/',os.sep))
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    try:
        d=urllib.request.urlopen(urllib.request.Request('https://res.zhuye.kim/'+p,headers=UA),timeout=20).read()
        open(dest,'wb').write(d); return ('ok',p,len(d))
    except Exception as e: return ('FAIL',p,str(e)[:50])

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    rs=list(ex.map(dl,missing))
print(f'Downloaded {sum(1 for r in rs if r[0]=="ok")} images, {sum(1 for r in rs if r[0]=="FAIL")} failed')
for r in rs:
    if r[0]=='FAIL': print('  FAIL',r)

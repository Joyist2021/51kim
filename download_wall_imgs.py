import json,re,os,urllib.request,concurrent.futures
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Referer':'https://www.51kim.com/'}
paths=set()
for fn in os.listdir('api'):
    if fn.startswith('bgimg_') and fn.endswith('.json'):
        obj=json.load(open('api/'+fn,encoding='utf-8'))
        body=obj.get('responseBody','') or ''
        paths|=set(re.findall(r'kimzhuye/[\w/.-]+?\.(?:png|jpg|jpeg|gif|html|htm)',body))
missing=[p for p in sorted(paths) if not os.path.exists(os.path.join('res',p.replace('/',os.sep)))]
print(f'total paths={len(paths)}, missing={len(missing)}',flush=True)
def dl(p):
    dest=os.path.join('res',p.replace('/',os.sep))
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    try:
        d=urllib.request.urlopen(urllib.request.Request('https://res.zhuye.kim/'+p,headers=UA),timeout=15).read()
        open(dest,'wb').write(d); return ('ok',p)
    except Exception as e: return ('FAIL',p,str(e)[:40])
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
    rs=list(ex.map(dl,missing))
print(f'ok={sum(1 for r in rs if r[0]=="ok")} fail={sum(1 for r in rs if r[0]=="FAIL")}',flush=True)
for r in rs:
    if r[0]=='FAIL': print('  FAIL',r,flush=True)

import urllib.request, json, re, os, concurrent.futures
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Referer':'https://www.51kim.com/'}
CATS={'1':'常用','230':'生活','105':'职能','63':'设计','74':'产品','96':'运营','267':'金融',
      '147':'综合','158':'商业','193':'科技','184':'名品','200':'机构','145':'大学'}
def fetch(kv):
    cid,name=kv
    url=f'https://www.51kim.com/front/site/get_list?id={cid}'
    data=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=25).read()
    obj=json.loads(data)
    open(f'api/site_{cid}.json','wb').write(data)
    return cid,name,obj,len(data)

results={}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for cid,name,obj,sz in ex.map(fetch,CATS.items()):
        results[cid]=(name,obj,sz)
        body=obj.get('responseBody','') or ''
        print(f'{cid:>4} {name:<4} saved {sz:>6}B, body {len(body)} chars, success={obj.get("success")}')

# collect all icon resource paths from all responses
all_icons=set()
for cid,(name,obj,sz) in results.items():
    body=obj.get('responseBody','') or ''
    all_icons|=set(re.findall(r'(?:group\d+/)?kimzhuye/[\w/.-]+\.(?:png|jpg|jpeg|gif)',body))
print('\nTotal unique icons across categories:',len(all_icons))

# find which are missing locally
missing=[p for p in sorted(all_icons) if not os.path.exists(os.path.join('res',p.replace('/',os.sep)))]
print('Missing icons:',len(missing))

def dl(p):
    url='https://res.zhuye.kim/'+p
    dest=os.path.join('res',p.replace('/',os.sep))
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    try:
        d=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=20).read()
        open(dest,'wb').write(d)
        return ('ok',p,len(d))
    except Exception as e: return ('FAIL',p,str(e)[:60])

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    rs=list(ex.map(dl,missing))
ok=[r for r in rs if r[0]=='ok']; fail=[r for r in rs if r[0]!='ok']
print(f'Downloaded {len(ok)} new icons, {len(fail)} failed')
for r in fail[:10]: print(' FAIL',r)

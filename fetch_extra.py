import urllib.request, json, re, os
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Referer':'https://www.51kim.com/'}
BASE='https://www.51kim.com'
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=25).read()

endpoints={
 'bgclass': f'{BASE}/front/bgclass/get_list?curReqMark=0',
 'bgimg_10': f'{BASE}/front/bgimg/get_list?classId=10&curReqMark=0',
 'share': f'{BASE}/front/share?_rd=0',
}
for name,url in endpoints.items():
    data=get(url)
    open(f'api/{name}.json','wb').write(data)
    obj=json.loads(data)
    print(f'{name}: {len(data)}B, body={len(obj.get("responseBody",""))} chars, success={obj.get("success")}')

# collect image paths from bgclass/bgimg/share data
allres=set()
for name in endpoints:
    obj=json.load(open(f'api/{name}.json',encoding='utf-8'))
    body=obj.get('responseBody','') or ''
    allres|=set(re.findall(r'(?:group\d+/)?kimzhuye/[\w/.-]+\.(?:png|jpg|jpeg|gif|html)',body))
    allres|=set(re.findall(r'(?:styles/front/)?img/[\w/.-]+\.(?:png|jpg|jpeg|gif)',body))
print('resource paths found:',len(allres))
# download under res/
import concurrent.futures
def dl(p):
    dest=os.path.join('res',p.replace('/',os.sep))
    if os.path.exists(dest): return ('skip',p)
    os.makedirs(os.path.dirname(dest),exist_ok=True)
    try:
        d=urllib.request.urlopen(urllib.request.Request('https://res.zhuye.kim/'+p,headers=UA),timeout=20).read()
        open(dest,'wb').write(d); return ('ok',p,len(d))
    except Exception as e: return ('FAIL',p,str(e)[:50])
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    rs=list(ex.map(dl,allres))
print('downloaded:',sum(1 for r in rs if r[0]=='ok'),'skipped:',sum(1 for r in rs if r[0]=='skip'),'failed:',sum(1 for r in rs if r[0]=='FAIL'))
for r in rs:
    if r[0]=='FAIL': print('  FAIL',r)

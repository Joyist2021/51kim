import os, re, concurrent.futures, urllib.request, urllib.error

RES='https://res.zhuye.kim'
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

html=open('index.original.html',encoding='utf-8').read()
js=open('assets/js/home.min.js',encoding='utf-8').read()
css=open('assets/css/home.min.css',encoding='utf-8').read()

tasks={}  # url -> local relative path (inside res/)
def add(url, local):
    tasks.setdefault(url, local)

# 1. embedded icons
icons=set(re.findall(r'(?:group\d+/)?kimzhuye/[\w/.-]+\.(?:png|jpg|jpeg|gif)', html))
icons|=set(re.findall(r'(?:group\d+/)?kimzhuye/[\w/.-]+\.(?:png|jpg|jpeg|gif)', js))
for p in icons: add(f'{RES}/{p}', p)

# 2. CSS url() assets
for u in set(re.findall(r'url\(([^)]+)\)', css)):
    u=u.strip('"\'')
    if u.startswith('data:'): continue
    if u.startswith('http'):
        path=u.split('/',3)[3] if u.count('/')>=3 else u
        add(u, path)
    elif u.startswith('../'):
        p='group0/home/'+u[3:]
        add(f'{RES}/{p}', p)

# 3. JS styles/front & img paths
for p in set(re.findall(r'(?:styles/front)?/[\w/.-]+\.(?:png|jpg|jpeg|gif|ico)', js)):
    p=p.lstrip('/')
    if p.startswith('styles/front/'):
        add(f'{RES}/{p}', p)
    elif p.startswith('img/'):
        full='styles/front/'+p
        add(f'{RES}/{full}', full)
    elif p=='favicon.ico':
        pass

# 4. help images (windows/... mac/...)
for p in set(re.findall(r'["\']((?:windows|mac)/[\w/.-]+\.(?:png|jpg))["\']', js)):
    full='styles/front/img/helpinfo/set-to-home/'+p
    add(f'{RES}/{full}', full)

# 5. video thumbnails (try styles/front/)
for name in ['custom-site-video.jpg','transparent-theme-video.png','color-theme-video.png']:
    full='styles/front/'+name
    add(f'{RES}/{full}', full)

# 6. search engine logos explicit
for p in ['styles/front/img/search/google-white.png','styles/front/img/search/baidu-white.png',
          'styles/front/img/userwebsite/default_site_icon.png','styles/front/img/usercenter/default_avatar.png',
          'styles/front/img/login/platform_wechat.png','styles/front/img/login/platform_weibo.png']:
    add(f'{RES}/{p}', p)

print(f'Total asset URLs to try: {len(tasks)}')

def fetch(item):
    url, local=item
    dest=os.path.join('res', local.replace('/', os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest)>0:
        return ('skip', local, os.path.getsize(dest))
    try:
        req=urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            data=r.read()
        if len(data)<20: return ('tiny', local, len(data))
        open(dest,'wb').write(data)
        return ('ok', local, len(data))
    except Exception as e:
        return ('FAIL', local, str(e)[:80])

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    for r in ex.map(fetch, tasks.items()):
        results.append(r)

ok=[r for r in results if r[0] in ('ok','skip')]
fail=[r for r in results if r[0] not in ('ok','skip')]
print(f'Downloaded/existing: {len(ok)}, failed: {len(fail)}')
print('Total bytes:', sum(r[2] for r in ok if isinstance(r[2],int)))
print('\nFailures (first 40):')
for r in fail[:40]: print('  ',r)

# favicon
try:
    req=urllib.request.Request('https://www.51kim.com/favicon.ico', headers=UA)
    data=urllib.request.urlopen(req,timeout=20).read()
    open('favicon.ico','wb').write(data)
    print('favicon:',len(data),'bytes')
except Exception as e:
    print('favicon failed:',e)

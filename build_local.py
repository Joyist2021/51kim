import re
BASE='http://127.0.0.1:8080'
html=open('index.original.html',encoding='utf-8').read()

def decode(s):
    n=int(s[0:3]); t=3+n; out=[]
    while t<len(s):
        l=int(s[t:t+3]); out.append(s[t+3:t+3+l]); t+=3+l
    return out

def encode(fields):
    s='000'
    for v in fields:
        v=str(v); s+=f'{len(v):03d}'+v
    return s

i=html.find("cfg: '")+6; j=html.find("'",i)
f=decode(html[i:j])
f[2]=BASE                  # serverURI
f[3]=BASE+'/meta-search'   # metaSearchURI
f[4]=BASE+'/res'           # resourceServerURI
f[5]=BASE+'/res/api'       # resourceServerAPIURI
f[15]='本地部署 · 资源已镜像至本机'  # footer note
html=html[:i]+encode(f)+html[j:]

html=html.replace('https://res.zhuye.kim/group0/home/css/kim.zhuye.front.home.min.css?v=1.8.2','assets/css/home.min.css')
html=html.replace('    <link href="assets/css/home.min.css"',
                  '    <link href="assets/css/local-auth.css" rel="stylesheet" type="text/css"/>\n    <link href="assets/css/home.min.css"',1)
html=html.replace('https://res.zhuye.kim/group0/home/js/kim.zhuye.front.home.min.js?v=1.9.3','assets/js/home.min.js')
# inject local SQLite auth UI script before </body>
html=html.replace('</body>', '    <script src="assets/js/local-auth.js"></script>\n</body>', 1)
html=html.replace('href="/favicon.ico"','href="favicon.ico"')
html=re.sub(r'<script>\s*var _hmt.*?</script>','',html,flags=re.S)
html=re.sub(r'<!--\[if lt IE 9\]>.*?<!\[endif\]-->','',html,flags=re.S)
open('index.html','w',encoding='utf-8').write(html)

css=open('assets/css/home.min.css',encoding='utf-8').read()
css=css.replace('https://res.zhuye.kim/','/res/')
css=re.sub(r'url\(\.\./img/loading\.gif\)','url(/res/styles/front/img/loading.gif)',css)
open('assets/css/home.min.css','w',encoding='utf-8').write(css)

js=open('assets/js/home.min.js',encoding='utf-8').read()
js=js.replace('https://res.hao1258.com/api','/res/api').replace('https://res.hao1258.com','/res')
js=js.replace('http://60.205.215.167',BASE)
open('assets/js/home.min.js','w',encoding='utf-8').write(js)
print('OK')

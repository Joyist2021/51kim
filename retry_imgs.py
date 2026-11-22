import os,urllib.request,time
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','Referer':'https://www.51kim.com/'}
# 15 timeout paths
fails=['kimzhuye/4b/ca/oJ6pHjd5ma-Fuqvi52-JqNIOG5yc_5703.jpg',
'kimzhuye/5b/75/oiFFU44j8EcVwTHoWzF9AkvYoZWY_7974.jpg',
'kimzhuye/61/20/o0CRD8rBid4JEdP07g8BTv79ejkc_3323.jpg',
'kimzhuye/65/13/oSCc5IJ0ydYRMpTRAPlptFGe0S0A_2541.jpg',
'kimzhuye/6a/39/oisTagk4lpwVYl5d9_2b8zym09wg_9503.jpg',
'kimzhuye/6a/c6/oLizZ5k8oytIW32FJNHkDEbcZBm0_1885.jpg',
'kimzhuye/70/ba/oGzdtT2p3vhdYQ1M6Ok2Ut47B_EA_4388.jpg',
'kimzhuye/79/20/oid1PEm3pw8pFwf2mNraDFo2_R4k_5161.jpg',
'kimzhuye/7d/ba/ozJXKK53mZcmsCzxTuks0780pfqw_7104.jpg',
'kimzhuye/83/45/oqOk1fB2gsYDDVwva4H-Zy_zV3GI_2596.jpg',
'kimzhuye/89/40/oJL5lyrkZCkGe2gD_ZtSRJVC5d6E_8459.jpg',
'kimzhuye/93/d1/okMbLKurwplM2hamIS1B55rewadM_0152.jpeg',
'kimzhuye/93/e6/ocfiA4qKNH47ksXw-TbIy-tmyHRA_9141.jpg',
'kimzhuye/9f/65/oEE6xcv8zRr58cuEwm3lszFTANKg_6470.jpg',
'kimzhuye/de/fd/oIspuC3ruADjgtLxB2NplnCbYbWk_3089.jpg']
# split the concatenated one properly
extra=['kimzhuye/fe/bc/oC1plpMoknf2jAaIYBjeBaFbOgaY_2090.JPG',
       'kimzhuye/ff/b8/o6tmDTV5HgOwUG7ZfJJjfa_8KyEU_5259.JPG',
       'kimzhuye/9f/16/o5hao35UrFSgW0SPVin6pj5slUQs_7644.jpg']
allp=fails+extra
ok=0
for p in allp:
    dest=os.path.join('res',p.replace('/',os.sep))
    if os.path.exists(dest) and os.path.getsize(dest)>0:
        ok+=1; continue
    for attempt in range(3):
        try:
            d=urllib.request.urlopen(urllib.request.Request('https://res.zhuye.kim/'+p,headers=UA),timeout=40).read()
            os.makedirs(os.path.dirname(dest),exist_ok=True)
            open(dest,'wb').write(d); ok+=1
            break
        except Exception as e:
            if attempt==2: print('FAIL',p,str(e)[:40],flush=True)
            time.sleep(1)
print(f'retry ok={ok}/{len(allp)}',flush=True)

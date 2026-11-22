#!/usr/bin/env python3
"""Build site_data.db from the captured 51kim data.

Normalizes the reverse-engineered SplitSet data into relational tables:
  - meta        : key/value (built version, notes)
  - categories  : category tabs (id, name, list=inner/outer, sort_order)
  - groups      : site groups within a category
  - sites       : individual navigation sites
  - header_icons: the 4 top-right header menu icons

The server reads these tables and re-encodes byte-exact SplitSet responses.
"""
import json
import os
import re
import sqlite3
import sys

import splitcodec as sc

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, 'site_data.db')
API_DIR = os.path.join(HERE, 'api')


def decode_cfg(html):
    """Decode the html config SplitSet into a list of fields."""
    i = html.find("cfg: '") + 6
    j = html.find("'", i)
    s = html[i:j]
    n = int(s[0:3]); t = 3 + n; out = []
    while t < len(s):
        l = int(s[t:t+3]); out.append(s[t+3:t+3+l]); t += 3 + l
    return out


def main():
    html = open(os.path.join(HERE, 'index.original.html'), encoding='utf-8').read()

    # ---- decode scgd (category tabs) : table 0 = inner, table 1 = outer ----
    i = html.find("scgd: '"); i = html.find("'", i) + 1
    scgd = html[i:html.find("'", i)]
    scgd_tables = sc.decode_splitset(scgd)

    categories = []  # (id, name, list, sort)
    for list_name, tbl in zip(('inner', 'outer'), scgd_tables):
        _, rows = sc.decode_table(tbl)
        for order, (gid, f) in enumerate(rows):
            # scgd row: group id empty; fields = [category_id, category_name]
            cid = f[0] if len(f) > 0 else gid
            cname = f[1] if len(f) > 1 else f[0]
            categories.append((cid, cname, list_name, order))

    # ---- sites: from api/site_*.json (13 categories) + csl embedded default ----
    # api json responseBody is a single SplitTable. Each table has groups + rows.
    category_tables = {}   # category_id -> encoded SplitTable string
    for fn in os.listdir(API_DIR):
        m = re.match(r'site_(\d+)\.json$', fn)
        if not m:
            continue
        cid = m.group(1)
        obj = json.load(open(os.path.join(API_DIR, fn), encoding='utf-8'))
        category_tables[cid] = obj.get('responseBody', '') or ''

    # embedded csl: table0 = category 1 (inner default), table1 = category 147 (outer default)
    i = html.find("csl: '"); i = html.find("'", i) + 1
    csl = html[i:html.find("'", i)]
    csl_tables = sc.decode_splitset(csl)
    if '1' not in category_tables:
        category_tables['1'] = csl_tables[0]
    if '147' not in category_tables:
        category_tables['147'] = csl_tables[1]

    # ---- header icons: from the hardcoded JS array ----
    header_icons = [
        # (id, title, icon_cls, hover_cls, menu_type, custom_style, sort_order, enabled, visible)
        ('user_center', '个人中心', 'user-center-icon', 'user-center-icon-hover', 'USER_CENTER', '', 0, 1, 1),
        ('bg_center',   '壁纸中心', 'bg-center-icon',   'bg-center-icon-hover',   'BG_CENTER',    '', 1, 1, 1),
        ('share',       '告诉朋友', 'share-icon',       'share-icon-hover',       'SHARE_WEBSITE', '', 2, 1, 1),
        ('info',        '信息中心', 'info-icon',        'info-icon-hover',        'HELP_INFO',     '', 3, 1, 1),
        ('back',        '返回',     'back-off-icon',    'back-off-icon-hover',    'GOUP',
         'display:none;margin-left:86px;width:32px;height:32px;top:-5px;', 4, 1, 1),
    ]

    # ------------------- write database -------------------
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript('''
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE categories (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            list_type TEXT NOT NULL, sort_order INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1, visible INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE groups (
            category_id TEXT NOT NULL, group_key TEXT NOT NULL, group_name TEXT NOT NULL,
            sort_order INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
            visible INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(category_id, group_key)
        );
        CREATE TABLE sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT NOT NULL, group_key TEXT NOT NULL,
            name TEXT NOT NULL, url TEXT NOT NULL, icon TEXT NOT NULL,
            raw_fields TEXT NOT NULL, sort_order INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1, visible INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE header_icons (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, icon_cls TEXT NOT NULL,
            hover_cls TEXT NOT NULL, menu_type TEXT NOT NULL, custom_style TEXT NOT NULL,
            sort_order INTEGER NOT NULL, enabled INTEGER NOT NULL,
            visible INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX idx_sites_cat ON sites(category_id);
        CREATE INDEX idx_groups_cat ON groups(category_id);
    ''')

    cur.executemany(
        'INSERT INTO categories (id,name,list_type,sort_order,enabled,visible) VALUES (?,?,?,?,1,1)',
        categories)
    cur.executemany(
        'INSERT INTO header_icons (id,title,icon_cls,hover_cls,menu_type,custom_style,sort_order,enabled,visible) '
        'VALUES (?,?,?,?,?,?,?,?,?)', header_icons)

    total_groups = total_sites = 0
    for cid, encoded in sorted(category_tables.items(), key=lambda x: int(x[0])):
        groups, rows = sc.decode_table(encoded)
        for order, (gkey, gname) in enumerate(groups):
            cur.execute('INSERT OR REPLACE INTO groups '
                        '(category_id,group_key,group_name,sort_order,enabled,visible) '
                        'VALUES (?,?,?,?,1,1)',
                        (cid, gkey, gname, order))
            total_groups += 1
        for order, (gkey, fields) in enumerate(rows):
            name = fields[0] if len(fields) > 0 else ''
            url = fields[1] if len(fields) > 1 else ''
            icon = fields[2] if len(fields) > 2 else ''
            cur.execute('INSERT INTO sites '
                        '(category_id,group_key,name,url,icon,raw_fields,sort_order,enabled,visible) '
                        'VALUES (?,?,?,?,?,?,?,1,1)',
                        (cid, gkey, name, url, icon,
                         json.dumps(fields, ensure_ascii=False), order))
            total_sites += 1

    cur.executemany('INSERT INTO meta VALUES (?,?)', [
        ('version', '1.0'),
        ('source', '51kim.com mirror - decoded SplitSet data'),
        ('category_count', str(len(categories))),
        ('group_count', str(total_groups)),
        ('site_count', str(total_sites)),
    ])
    con.commit()
    con.close()

    print(f'DB written: {DB_PATH}')
    print(f'  categories : {len(categories)}')
    print(f'  groups     : {total_groups}')
    print(f'  sites      : {total_sites}')
    print(f'  header icons: {len(header_icons)}')

    # verify round-trip: rebuild each category table from DB and compare
    con = sqlite3.connect(DB_PATH)
    ok = True
    for cid, encoded in category_tables.items():
        groups = [r[0:2] for r in con.execute(
            'SELECT group_key,group_name FROM groups WHERE category_id=? ORDER BY sort_order', (cid,))]
        sites = []
        for row in con.execute('SELECT group_key,name,url,icon FROM sites WHERE category_id=? ORDER BY sort_order', (cid,)):
            sites.append({'group_id': row[0], 'raw_fields': [row[1], row[2], row[3]]})
        rebuilt = sc.sites_to_table(groups, sites)
        if rebuilt != encoded:
            ok = False
            print(f'  ROUNDTRIP MISMATCH for category {cid}')
    con.close()
    print(f'  round-trip all categories: {"OK" if ok else "FAILED"}')
    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()

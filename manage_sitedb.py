#!/usr/bin/env python3
"""Manage the local site SQLite DB (sitedata.db).

Examples:
  python manage_sitedb.py list categories
  python manage_sitedb.py list sites 230
  python manage_sitedb.py list icons
  python manage_sitedb.py add-site 230 231 "新站点" "https://example.com/" kimzhuye/xx/xx/icon.png
  python manage_sitedb.py rename-site 1 "新名称"
  python manage_sitedb.py del-site 1
  python manage_sitedb.py add-icon "我的入口" my-icon my-icon-hover HELP_INFO
  python manage_sitedb.py set-icon 1 title "新标题"
  python manage_sitedb.py rebuild       # re-import everything from captured data
"""
import os
import sqlite3
import subprocess
import sys

import admin_db

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'site_data.db')


def conn():
    if not os.path.exists(DB):
        subprocess.run([sys.executable, os.path.join(HERE, 'build_sitedb.py')], check=True)
    admin_db.ensure_site_schema()
    return sqlite3.connect(DB)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]

    if cmd == 'rebuild':
        subprocess.run([sys.executable, os.path.join(HERE, 'build_sitedb.py')], check=True)
        print('Done. Restart the server to pick up changes.')
        return

    c = conn()

    if cmd == 'list' and len(args) >= 2 and args[1] == 'categories':
        for r in c.execute('SELECT id,name,list_type,sort_order FROM categories ORDER BY list_type,sort_order'):
            print(f'  {r[0]:>4}  {r[1]:<8} [{r[2]}]  #{r[3]}')
    elif cmd == 'list' and len(args) >= 2 and args[1] == 'sites':
        cid = args[2] if len(args) > 2 else '1'
        for r in c.execute('SELECT id,name,url FROM sites WHERE category_id=? ORDER BY sort_order', (cid,)):
            print(f'  {r[0]:>4}  {r[1]:<16} {r[2]}')
    elif cmd == 'list' and len(args) >= 2 and args[1] in ('icons', 'header'):
        for r in c.execute('SELECT id,title,menu_type,enabled,visible,sort_order FROM header_icons ORDER BY sort_order'):
            print(f'  {r[0]:<12} {r[1]:<8} {r[2]:<14} enabled={r[3]} visible={r[4]} #{r[5]}')

    elif cmd == 'add-site' and len(args) >= 6:
        cid, gkey, name, url, icon = args[1:6]
        order = c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 FROM sites WHERE category_id=?', (cid,)).fetchone()[0]
        c.execute('INSERT OR IGNORE INTO groups '
                  '(category_id,group_key,group_name,sort_order,enabled,visible) VALUES (?,?,?,?,1,1)',
                  (cid, gkey, gkey, 99))
        c.execute('INSERT INTO sites '
                  '(category_id,group_key,name,url,icon,raw_fields,sort_order,enabled,visible) '
                  'VALUES (?,?,?,?,?,?,?,1,1)',
                  (cid, gkey, name, url, icon, '[]', order))
        c.commit()
        print(f'Added site "{name}" to category {cid}.')
    elif cmd == 'rename-site' and len(args) >= 3:
        c.execute('UPDATE sites SET name=? WHERE id=?', (args[2], args[1]))
        c.commit(); print('Renamed.')
    elif cmd == 'del-site' and len(args) >= 2:
        c.execute('DELETE FROM sites WHERE id=?', (args[1],))
        c.commit(); print('Deleted.')
    elif cmd == 'del-name' and len(args) >= 2:
        c.execute('DELETE FROM sites WHERE name=?', (args[1],))
        c.commit(); print(f'Deleted {c.total_changes} row(s).')

    elif cmd == 'add-icon' and len(args) >= 5:
        iid, title, icls, hcls = args[1], args[2], args[3], args[4]
        mtype = args[5] if len(args) > 5 else 'HELP_INFO'
        order = c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 FROM header_icons').fetchone()[0]
        c.execute('INSERT OR REPLACE INTO header_icons '
                  '(id,title,icon_cls,hover_cls,menu_type,custom_style,sort_order,enabled,visible) '
                  'VALUES (?,?,?,?,?,?,?,?,?)',
                  (iid, title, icls, hcls, mtype, '', order, 1, 1))
        c.commit(); print(f'Added header icon "{title}".')
    elif cmd == 'set-icon' and len(args) >= 4:
        iid, field, value = args[1], args[2], args[3]
        allowed = {'title', 'icon_cls', 'hover_cls', 'menu_type', 'custom_style',
                   'enabled', 'visible', 'sort_order'}
        if field not in allowed:
            print('Allowed fields:', ', '.join(sorted(allowed))); return
        c.execute(f'UPDATE header_icons SET {field}=? WHERE id=?', (value, iid))
        c.commit(); print('Updated.')

    else:
        print('Unknown command. Run without arguments to see usage.')
    c.close()
    print('Tip: refresh the browser; changes take effect immediately (server reads DB per request).')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Generate frontend config strings from site_data.db.

Produces:
  - scgd : SplitSet of category tabs (table 0 = inner, table 1 = outer)
  - csl  : SplitSet of default site lists (table 0 = cat 1, table 1 = cat 147)
  - headerIcons : JS array literal for the 4 top-right icons
"""
import json
import os
import sqlite3

import admin_db
import splitcodec as sc

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_DB = os.path.join(HERE, 'site_data.db')


def _connect():
    conn = sqlite3.connect(SITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def build_scgd(conn):
    """Category tabs -> SplitSet (2 tables: inner, outer)."""
    tables = []
    for list_type in ('inner', 'outer'):
        rows = conn.execute(
            'SELECT id, name FROM categories '
            'WHERE list_type=? AND enabled=1 AND visible=1 ORDER BY sort_order',
            (list_type,)).fetchall()
        # each scgd row: empty group id, fields = [category_id, category_name]
        data_rows = [('', [r['id'], r['name']]) for r in rows]
        tables.append(sc.encode_table([], data_rows))
    return sc.encode_splitset(tables)


def build_csl(conn):
    """Default site lists -> SplitSet (table 0 = cat 1 inner, table 1 = cat 147 outer)."""
    tables = []
    for cid in ('1', '147'):
        groups = [(r['group_key'], r['group_name']) for r in conn.execute(
            'SELECT group_key, group_name FROM groups '
            'WHERE category_id=? AND enabled=1 AND visible=1 ORDER BY sort_order',
            (cid,))]
        sites = []
        for r in conn.execute(
                'SELECT group_key, name, url, icon FROM sites '
                'WHERE category_id=? AND enabled=1 AND visible=1 ORDER BY sort_order',
                (cid,)):
            sites.append({'group_id': r['group_key'],
                          'raw_fields': [r['name'], r['url'], r['icon']]})
        tables.append(sc.sites_to_table(groups, sites))
    return sc.encode_splitset(tables)


def build_header_icons(conn):
    """Header icons -> JS array literal (only enabled ones, ordered)."""
    icons = []
    for r in conn.execute(
            'SELECT * FROM header_icons WHERE enabled=1 AND visible=1 ORDER BY sort_order'):
        entry = {'menuTitle': r['title'], 'menuIconCls': r['icon_cls'],
                 'menuHoverIconCls': r['hover_cls'], 'menuType': r['menu_type']}
        if r['custom_style']:
            entry['customStyle'] = r['custom_style']
        icons.append(entry)
    # JSON is valid JS object literal; emit indented for readability
    return json.dumps(icons, ensure_ascii=False)


def build_all():
    admin_db.ensure_site_schema()
    conn = _connect()
    try:
        return {
            'scgd': build_scgd(conn),
            'csl': build_csl(conn),
            'headerIcons': build_header_icons(conn),
        }
    finally:
        conn.close()


if __name__ == '__main__':
    cfg = build_all()
    print('scgd len:', len(cfg['scgd']))
    print('csl  len:', len(cfg['csl']))
    print('header icons:', cfg['headerIcons'])

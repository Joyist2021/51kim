#!/usr/bin/env python3
"""Byte-exact codec for the 51kim 'SplitSet' length-prefix encoding.

Formats observed in the wild:

  SplitDataRow = [3-digit gidLen][gid][3-digit fieldLen][field]...
  SplitTable   = [4-digit groupBlockLen][groupBlock][6-digit rowLen][row]...
      where groupBlock = [2-digit entryLen][2-digit idLen][id][name]...
  SplitSet     = [10-digit tableLen][SplitTable]...   (used by csl / scgd)

A site_*.json responseBody is a *single* SplitTable (no 10-digit wrapper).
The embedded `csl` / `scgd` are SplitSets (with the 10-digit wrapper).
"""


# ---------------------------------------------------------------- decode ----
def decode_row(row):
    """SplitDataRow -> (group_id, [fields...])."""
    n = int(row[0:3]); t = 3 + n
    gid = row[3:3 + n] if n else ''
    fields = []
    while t < len(row):
        l = int(row[t:t + 3])
        fields.append(row[t + 3:t + 3 + l])
        t += 3 + l
    return gid, fields


def decode_table(tbl):
    """SplitTable -> ([(gid, name)...], [(gid, fields)...])."""
    gn = int(tbl[0:4]); gp = tbl[4:4 + gn]
    groups = []
    g = 0
    while g < len(gp):
        el = int(gp[g:g + 2])
        blk = gp[g + 2:g + 2 + el]
        nid = int(blk[0:2])
        groups.append((blk[2:2 + nid], blk[2 + nid:]))
        g += 2 + el
    rows = []
    r = 4 + gn
    while r + 6 <= len(tbl):
        l = int(tbl[r:r + 6])
        if l == 0 or r + 6 + l > len(tbl):
            break
        rows.append(decode_row(tbl[r + 6:r + 6 + l]))
        r += 6 + l
    return groups, rows


def decode_splitset(s):
    """SplitSet -> [SplitTable strings]."""
    tables = []
    t = 0
    while t + 10 <= len(s):
        l = int(s[t:t + 10])
        if l == 0 or t + 10 + l > len(s):
            break
        tables.append(s[t + 10:t + 10 + l])
        t += 10 + l
    return tables


# ---------------------------------------------------------------- encode ----
def encode_row(gid, fields):
    gid = str(gid)
    out = f'{len(gid):03d}' + gid
    for f in fields:
        f = str(f)
        out += f'{len(f):03d}' + f
    return out


def encode_table(groups, rows):
    """groups: [(gid,name)], rows: [(gid, fields)]."""
    gp = ''
    for gid, name in groups:
        gid, name = str(gid), str(name)
        blk = f'{len(gid):02d}' + gid + name
        gp += f'{len(blk):02d}' + blk
    out = f'{len(gp):04d}' + gp
    for gid, fields in rows:
        row = encode_row(gid, fields)
        out += f'{len(row):06d}' + row
    return out


def encode_splitset(tables):
    out = ''
    for t in tables:
        out += f'{len(t):010d}' + t
    return out


# ------------------------------------------------------------- high-level ---
def table_to_sites(tbl):
    """SplitTable -> {'groups': [(gid,name)], 'sites': [dict]}"""
    groups, rows = decode_table(tbl)
    sites = []
    for gid, f in rows:
        # fields: [name, url, icon, ...maybe more]
        sites.append({'group_id': gid, 'name': f[0] if len(f) > 0 else '',
                      'url': f[1] if len(f) > 1 else '',
                      'icon': f[2] if len(f) > 2 else '',
                      'raw_fields': f})
    return {'groups': groups, 'sites': sites}


def sites_to_table(groups, sites):
    """inverse of table_to_sites."""
    rows = [(s['group_id'], s['raw_fields']) for s in sites]
    return encode_table(groups, rows)

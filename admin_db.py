#!/usr/bin/env python3
"""SQLite helpers for the local admin console.

Manages:
  - admin account / admin sessions (stored in users.db)
  - schema migration and CRUD for site_data.db
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time

HERE = os.path.dirname(os.path.abspath(__file__))
USERS_DB = os.path.join(HERE, 'users.db')
SITE_DB = os.path.join(HERE, 'site_data.db')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '123456'
ADMIN_SESSION_COOKIE = 'kim_admin_session'
ADMIN_SESSION_TTL = 7 * 24 * 3600

TABLES = {
    'categories': {
        'label': '分类标签',
        'fields': ['id', 'name', 'list_type', 'sort_order', 'enabled', 'visible'],
        'ints': ['sort_order', 'enabled', 'visible'],
        'immutable_on_update': ['id'],
        'required': ['id', 'name', 'list_type'],
        'order': 'sort_order, id',
    },
    'groups': {
        'label': '站点分组',
        'fields': ['category_id', 'group_key', 'group_name', 'sort_order', 'enabled', 'visible'],
        'ints': ['sort_order', 'enabled', 'visible'],
        'immutable_on_update': ['category_id', 'group_key'],
        'required': ['category_id', 'group_key', 'group_name'],
        'order': 'category_id, sort_order, group_key',
    },
    'sites': {
        'label': '站点条目',
        'fields': ['id', 'category_id', 'group_key', 'name', 'url', 'icon', 'sort_order', 'enabled', 'visible'],
        'ints': ['sort_order', 'enabled', 'visible'],
        'immutable_on_update': ['id'],
        'required': ['category_id', 'group_key', 'name', 'url', 'icon'],
        'order': 'category_id, sort_order, id',
    },
    'icons': {
        'label': '顶部图标',
        'fields': ['id', 'title', 'icon_cls', 'hover_cls', 'menu_type', 'custom_style',
                   'sort_order', 'enabled', 'visible'],
        'ints': ['sort_order', 'enabled', 'visible'],
        'immutable_on_update': ['id'],
        'required': ['id', 'title', 'icon_cls', 'hover_cls', 'menu_type'],
        'order': 'sort_order, id',
    },
    'users': {
        'label': '注册用户',
        'fields': ['id', 'username', 'nickname', 'email', 'created_at', 'last_login'],
        'ints': ['id'],
        'immutable_on_update': ['id', 'created_at', 'last_login'],
        'required': ['username'],
        'order': 'id',
    },
}

REAL_TABLE = {'icons': 'header_icons'}


def _db_path(kind):
    return USERS_DB if kind == 'users' else SITE_DB


def _table(kind):
    if kind not in TABLES:
        raise ValueError('未知数据类型: ' + str(kind))
    return REAL_TABLE.get(kind, kind)


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 120000)
    return salt + ':' + dk.hex()


def _verify_password(password, stored):
    try:
        salt, _ = stored.split(':', 1)
        return hmac.compare_digest(_hash_password(password, salt), stored)
    except Exception:
        return False


# ------------------------------------------------------------- schema ----
def ensure_site_schema():
    """Add admin flags to an existing site_data.db without touching data."""
    if not os.path.exists(SITE_DB):
        return
    conn = sqlite3.connect(SITE_DB)
    try:
        for kind in TABLES:
            if kind == 'users':
                continue
            table = _table(kind)
            cols = {r[1] for r in conn.execute('PRAGMA table_info(%s)' % table)}
            for col in ('enabled', 'visible'):
                if col not in cols:
                    conn.execute('ALTER TABLE %s ADD COLUMN %s INTEGER NOT NULL DEFAULT 1' % (table, col))
        conn.commit()
    finally:
        conn.close()


def ensure_admin_account():
    if not os.path.exists(USERS_DB):
        return
    conn = sqlite3.connect(USERS_DB)
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS admin_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )''')
        row = conn.execute('SELECT username FROM admin_users WHERE username=?',
                           (ADMIN_USERNAME,)).fetchone()
        if not row:
            conn.execute('INSERT INTO admin_users (username,password_hash) VALUES (?,?)',
                         (ADMIN_USERNAME, _hash_password(ADMIN_PASSWORD)))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------- admin auth ----
def verify_admin_login(username, password):
    conn = sqlite3.connect(USERS_DB)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT username,password_hash FROM admin_users WHERE username=?',
                           (str(username).strip(),)).fetchone()
        if not row or not _verify_password(str(password), row['password_hash']):
            return None
        return {'username': row['username']}
    finally:
        conn.close()


def change_admin_password(username, old_password, new_password):
    """Verify the old admin password and store a fresh PBKDF2 hash."""
    new_password = str(new_password)
    if len(new_password) < 6:
        return {'success': False, 'message': '新密码至少 6 位'}
    conn = sqlite3.connect(USERS_DB)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT password_hash FROM admin_users WHERE username=?',
                           (username,)).fetchone()
        if not row or not _verify_password(str(old_password), row['password_hash']):
            return {'success': False, 'message': '当前密码错误'}
        conn.execute('UPDATE admin_users SET password_hash=? WHERE username=?',
                     (_hash_password(new_password), username))
        conn.commit()
        return {'success': True, 'message': '管理员密码已修改'}
    finally:
        conn.close()


def create_admin_session(username):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    conn = sqlite3.connect(USERS_DB)
    try:
        conn.execute('INSERT INTO admin_sessions (token,username,created_at,expires_at) VALUES (?,?,?,?)',
                     (token, username, now, now + ADMIN_SESSION_TTL))
        conn.commit()
    finally:
        conn.close()
    return token


def admin_session_from_headers(headers):
    for part in headers.get('Cookie', '').split(';'):
        part = part.strip()
        if part.startswith(ADMIN_SESSION_COOKIE + '='):
            return part.split('=', 1)[1]
    return None


def current_admin(headers):
    token = admin_session_from_headers(headers)
    if not token:
        return None
    conn = sqlite3.connect(USERS_DB)
    try:
        row = conn.execute('SELECT username FROM admin_sessions WHERE token=? AND expires_at>?',
                           (token, int(time.time()))).fetchone()
        return {'username': row[0]} if row else None
    finally:
        conn.close()


def delete_admin_session(token):
    if not token:
        return
    conn = sqlite3.connect(USERS_DB)
    try:
        conn.execute('DELETE FROM admin_sessions WHERE token=?', (token,))
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------ site CRUD ---
def list_rows(kind):
    meta = TABLES[kind]
    table = _table(kind)
    cols = ', '.join(['rowid AS _rowid'] + meta['fields'])
    conn = sqlite3.connect(_db_path(kind))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute('SELECT %s FROM %s ORDER BY %s' % (cols, table, meta['order'])).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_rows():
    out = {}
    for kind in TABLES:
        path = _db_path(kind)
        if not os.path.exists(path):
            out[kind] = 0
            continue
        conn = sqlite3.connect(path)
        try:
            out[kind] = conn.execute('SELECT COUNT(*) FROM %s' % _table(kind)).fetchone()[0]
        except sqlite3.OperationalError:
            out[kind] = 0
        finally:
            conn.close()
    return out


def _clean_fields(kind, raw, creating=False):
    meta = TABLES[kind]
    cleaned = {}
    for field in meta['fields']:
        if field not in raw:
            continue
        value = raw.get(field)
        if field in meta['ints']:
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = 0
            if field in ('enabled', 'visible'):
                value = 1 if value else 0
        else:
            value = '' if value is None else str(value)
        cleaned[field] = value
    if creating:
        for field in meta['required']:
            if field not in cleaned or (isinstance(cleaned[field], str) and not cleaned[field].strip()):
                raise ValueError('缺少必填字段: ' + field)
        if kind != 'users':
            cleaned.setdefault('enabled', 1)
            cleaned.setdefault('visible', 1)
        if kind == 'icons':
            cleaned.setdefault('custom_style', '')
    return cleaned


def _next_sort(conn, kind):
    table = _table(kind)
    row = conn.execute('SELECT COALESCE(MAX(sort_order), -1) + 1 FROM %s' % table).fetchone()
    return int(row[0])


def insert_row(kind, raw):
    meta = TABLES[kind]
    table = _table(kind)
    values = _clean_fields(kind, raw, creating=True)

    # id is an AUTOINCREMENT primary key for sites/users; an empty form field
    # must not override it with 0 (otherwise rowid 0 breaks edit/delete APIs).
    if kind in ('sites', 'users') and values.get('id') in (0, '0', ''):
        values.pop('id', None)

    if kind == 'users':
        password = str(raw.get('password', ''))
        if len(password) < 6:
            return {'success': False, 'message': '密码至少 6 位'}
        values.pop('created_at', None)
        values.pop('last_login', None)
        values.setdefault('nickname', values.get('username', ''))
        values.setdefault('email', '')
        values['password_hash'] = _hash_password(password)
    else:
        if 'sort_order' not in values:
            values['sort_order'] = _next_sort_for_new(kind)
        if kind == 'sites' and not values.get('raw_fields'):
            values['raw_fields'] = json.dumps(
                [values.get('name', ''), values.get('url', ''), values.get('icon', '')],
                ensure_ascii=False)

    columns = list(values.keys())
    sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
        table, ','.join(columns), ','.join('?' for _ in columns))
    conn = sqlite3.connect(_db_path(kind))
    try:
        conn.execute(sql, [values[c] for c in columns])
        if kind == 'sites':
            conn.execute('UPDATE sites SET raw_fields=? WHERE rowid=last_insert_rowid()',
                         (json.dumps([values.get('name', ''), values.get('url', ''),
                                      values.get('icon', '')], ensure_ascii=False),))
        conn.commit()
        return {'success': True, 'message': '已新增'}
    except sqlite3.IntegrityError as e:
        return {'success': False, 'message': '新增失败：值重复或无效（%s）' % e}
    finally:
        conn.close()


def _next_sort_for_new(kind):
    conn = sqlite3.connect(SITE_DB)
    try:
        return _next_sort(conn, kind)
    finally:
        conn.close()


def update_row(kind, rowid, raw):
    meta = TABLES[kind]
    table = _table(kind)
    values = _clean_fields(kind, raw)
    for field in meta['immutable_on_update']:
        values.pop(field, None)
    password = str(raw.get('password', '') or '')
    if kind == 'users' and password:
        if len(password) < 6:
            return {'success': False, 'message': '密码至少 6 位'}
        values['password_hash'] = _hash_password(password)
    if not values:
        return {'success': False, 'message': '没有可更新的字段'}
    columns = list(values.keys())
    sql = 'UPDATE %s SET %s WHERE rowid=?' % (
        table, ','.join('%s=?' % c for c in columns))
    params = [values[c] for c in columns] + [rowid]
    conn = sqlite3.connect(_db_path(kind))
    try:
        conn.execute(sql, params)
        if kind == 'sites' and any(k in values for k in ('name', 'url', 'icon')):
            row = conn.execute('SELECT name,url,icon FROM sites WHERE rowid=?', (rowid,)).fetchone()
            if row:
                conn.execute('UPDATE sites SET raw_fields=? WHERE rowid=?',
                             (json.dumps(list(row), ensure_ascii=False), rowid))
        conn.commit()
        return {'success': True, 'message': '已保存'}
    except sqlite3.IntegrityError as e:
        return {'success': False, 'message': '保存失败：值重复或无效（%s）' % e}
    finally:
        conn.close()


def delete_row(kind, rowid):
    table = _table(kind)
    conn = sqlite3.connect(_db_path(kind))
    try:
        if kind == 'users':
            row = conn.execute('SELECT id FROM users WHERE rowid=?', (rowid,)).fetchone()
            if not row:
                return {'success': False, 'message': '未找到该条目'}
            conn.execute('DELETE FROM sessions WHERE user_id=?', (row[0],))
        cur = conn.execute('DELETE FROM %s WHERE rowid=?' % table, (rowid,))
        conn.commit()
        if cur.rowcount == 0:
            return {'success': False, 'message': '未找到该条目'}
        return {'success': True, 'message': '已删除'}
    finally:
        conn.close()


def set_flag(kind, rowid, field, value):
    if field not in ('enabled', 'visible'):
        return {'success': False, 'message': '不支持的标记字段'}
    table = _table(kind)
    flag = 1 if str(value).lower() in ('1', 'true', 'yes', 'on') else 0
    conn = sqlite3.connect(_db_path(kind))
    try:
        conn.execute('UPDATE %s SET %s=? WHERE rowid=?' % (table, field), (flag, rowid))
        conn.commit()
        return {'success': True, 'message': '已更新'}
    finally:
        conn.close()

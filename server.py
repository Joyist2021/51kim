#!/usr/bin/env python3
"""Local server for 51kim mirror.

- Static file serving
- Captured per-category site lists / wallpaper / share data
- SQLite-backed local user authentication (register / login / logout / me / change password)
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import admin_db
import db_config
import splitcodec as sc

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
ROOT = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(ROOT, 'api')
DB_PATH = os.path.join(ROOT, 'users.db')
SITE_DB = os.path.join(ROOT, 'site_data.db')
SESSION_COOKIE = 'kim_session'
SESSION_TTL = 7 * 24 * 3600  # 7 days

# ---------------------------------------------------------------- SQLite ----
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email         TEXT DEFAULT '',
        nickname      TEXT DEFAULT '',
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        last_login    TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        token      TEXT PRIMARY KEY,
        user_id    INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
    )''')
    conn.commit()
    conn.close()
    admin_db.ensure_admin_account()
    admin_db.ensure_site_schema()


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 120000)
    return salt + ':' + dk.hex()


def verify_password(password, stored):
    try:
        salt, _ = stored.split(':', 1)
        return hmac.compare_digest(hash_password(password, salt), stored)
    except Exception:
        return False


def session_token_from_headers(headers):
    for part in headers.get('Cookie', '').split(';'):
        part = part.strip()
        if part.startswith(SESSION_COOKIE + '='):
            return part.split('=', 1)[1]
    return None


def current_user(headers):
    token = session_token_from_headers(headers)
    if not token:
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT u.id, u.username, u.nickname, u.email
                 FROM sessions s JOIN users u ON u.id = s.user_id
                 WHERE s.token = ? AND s.expires_at > ?''', (token, int(time.time())))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def public_user(row):
    return {'id': row['id'], 'username': row['username'],
            'nickname': row['nickname'] or row['username'], 'email': row['email']}


# --------------------------------------------------- SQLite site data helpers --
def site_category_table(cid):
    """Build a SplitTable string for a category from site_data.db (byte-exact)."""
    if not os.path.exists(SITE_DB):
        return None
    conn = sqlite3.connect(SITE_DB)
    try:
        groups = [(r[0], r[1]) for r in conn.execute(
            'SELECT group_key,group_name FROM groups '
            'WHERE category_id=? AND enabled=1 AND visible=1 ORDER BY sort_order', (cid,))]
        sites = []
        for r in conn.execute(
                'SELECT group_key,name,url,icon FROM sites '
                'WHERE category_id=? AND enabled=1 AND visible=1 ORDER BY sort_order', (cid,)):
            sites.append({'group_id': r[0], 'raw_fields': [r[1], r[2], r[3]]})
        if not groups and not sites:
            return None
        return sc.sites_to_table(groups, sites)
    finally:
        conn.close()


def db_config_js():
    """Generate JS that exposes DB-driven config to the page."""
    cfg = db_config.build_all()
    return ('window.KIM_DB_CONFIG = '
            + json.dumps({'scgd': cfg['scgd'], 'csl': cfg['csl'],
                          'headerIcons': json.loads(cfg['headerIcons'])}, ensure_ascii=False)
            + ';')


# ----------------------------------------------------------- captured API ---
STUBS = {
    '/front/animation/weather':   {'success': True, 'responseBody': {'weather': ''}},
    '/front/notice/list/head':    {'success': True, 'responseBody': []},
    '/front/registeruser_site/get_list': {'success': True, 'responseBody': ''},
    '/front/helpinfo':            {'success': True, 'responseBody': ''},
    '/meta-search':               None,  # handled specially
}

SITE_CACHE = {}
if os.path.isdir(API_DIR):
    for fn in os.listdir(API_DIR):
        if fn.startswith('site_') and fn.endswith('.json'):
            with open(os.path.join(API_DIR, fn), 'rb') as f:
                SITE_CACHE[fn[5:-5]] = f.read()

RAW_API = {}
for key, fn in (('bgclass', 'bgclass.json'), ('share', 'share.json')):
    p = os.path.join(API_DIR, fn)
    if os.path.exists(p):
        with open(p, 'rb') as f:
            RAW_API[key] = f.read()

# Wallpaper lists, keyed by classId string (10=动态,2=风景,4=素雅,5=唯美,6=纯色,7=静物,8=星空,9=城市,11=人物)
BGIMG_CACHE = {}
if os.path.isdir(API_DIR):
    for fn in os.listdir(API_DIR):
        m = re.match(r'bgimg_(\d+)\.json$', fn)
        if m:
            with open(os.path.join(API_DIR, fn), 'rb') as f:
                BGIMG_CACHE[m.group(1)] = f.read()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    # -------------------------------------------------------------- helpers --
    def _send_bytes(self, data, ctype='application/json; charset=utf-8'):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, extra_headers=None, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return parse_qs(raw.decode('utf-8', 'ignore'), keep_blank_values=True)

    def _echo_mark(self, obj, mark):
        if mark:
            obj['curReqMark'] = mark
        return obj

    def _require_admin(self):
        admin = admin_db.current_admin(self.headers)
        if not admin:
            self._json({'success': False, 'message': '请先登录管理后台'}, status=401)
            return None
        return admin

    def _serve_admin(self):
        path = os.path.join(ROOT, 'admin.html')
        with open(path, encoding='utf-8') as f:
            data = f.read().encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _serve_index(self):
        """Serve index.html with scgd/csl/header icons injected from SQLite."""
        path = os.path.join(ROOT, 'index.html')
        with open(path, encoding='utf-8') as f:
            html = f.read()
        try:
            cfg = db_config.build_all()
            # Replace the inline scgd / csl string literals with DB-generated ones
            html = re.sub(r"(scgd:\s*')[^']*(')", lambda m: m.group(1) + cfg['scgd'] + m.group(2), html, count=1)
            html = re.sub(r"(csl:\s*')[^']*(')", lambda m: m.group(1) + cfg['csl'] + m.group(2), html, count=1)
            # Inject DB config as a plain JS statement inside the existing inline
            # script block (before loadScript), so it is defined when home.min.js boots.
            marker = 'loadScript(__sys_js_lib_path'
            inject = ('var KIM_DB_CONFIG={headerIcons:'
                      + cfg['headerIcons'] + '};\n    ')
            if marker in html and 'KIM_DB_CONFIG' not in html:
                html = html.replace(marker, inject + marker, 1)
        except Exception as e:
            # On any DB error, fall back to the static index.html unchanged
            print('index injection error:', e, file=sys.stderr)
        data = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------------ GET --
    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)

        # ---- admin console ----
        if path in ('/admin', '/admin/'):
            self._serve_admin()
            return

        if path == '/admin/api/session':
            admin = admin_db.current_admin(self.headers)
            self._json({'success': True, 'authenticated': bool(admin), 'user': admin})
            return

        if path == '/admin/api/overview':
            if not self._require_admin():
                return
            self._json({'success': True, 'counts': admin_db.count_rows()})
            return

        if path == '/admin/api/data':
            if not self._require_admin():
                return
            kind = qs.get('type', ['categories'])[0]
            try:
                meta = admin_db.TABLES[kind]
                payload = {
                    'success': True,
                    'type': kind,
                    'label': meta['label'],
                    'columns': meta['fields'],
                    'immutable': meta['immutable_on_update'],
                    'rows': admin_db.list_rows(kind),
                    'counts': admin_db.count_rows(),
                }
                self._json(payload)
            except ValueError as e:
                self._json({'success': False, 'message': str(e)}, status=400)
            return

        # ---- auth ----
        if path == '/auth/me':
            user = current_user(self.headers)
            self._json({'success': True, 'user': public_user(user) if user else None})
            return

        # ---- DB-driven app config (scgd / csl / header icons) ----
        if path == '/app-config.js':
            js = db_config_js()
            self._send_bytes(js.encode('utf-8'), ctype='application/javascript; charset=utf-8')
            return

        # ---- home.min.js with header icons sourced from SQLite ----
        if path.endswith('home.min.js'):
            js_path = os.path.join(ROOT, 'assets', 'js', 'home.min.js')
            with open(js_path, encoding='utf-8') as f:
                js = f.read()
            try:
                cfg = db_config.build_all()
                icons = cfg['headerIcons']  # JS array literal string
                start_marker = 'headerMenuData:['
                end_marker = '],immediatelyRuns:'
                si = js.find(start_marker)
                ei = js.find(end_marker, si)
                if si >= 0 and ei > si:
                    js = js[:si] + 'headerMenuData:' + icons + js[ei + 1:]
            except Exception as e:
                print('home.min.js injection error:', e, file=sys.stderr)
            self._send_bytes(js.encode('utf-8'), ctype='application/javascript; charset=utf-8')
            return

        # ---- index.html: inject DB-driven header icons into the page ----
        if path in ('/', '/index.html'):
            self._serve_index()
            return

        # ---- category site lists (from SQLite) ----
        if path == '/front/site/get_list':
            cid = qs.get('id', [''])[0]
            mark = qs.get('curReqMark', [''])[0]
            table = site_category_table(cid)
            if table is not None:
                self._json(self._echo_mark({'success': True, 'responseBody': table}, mark))
            else:
                self._json({'success': True, 'responseBody': '', 'curReqMark': mark})
            return

        # ---- wallpaper classes ----
        if path == '/front/bgclass/get_list':
            mark = qs.get('curReqMark', [''])[0]
            raw = RAW_API.get('bgclass')
            if raw:
                self._json(self._echo_mark(json.loads(raw), mark))
            else:
                self._json({'success': True, 'responseBody': '', 'curReqMark': mark})
            return

        # ---- wallpaper images (all categories) ----
        if path == '/front/bgimg/get_list':
            mark = qs.get('curReqMark', [''])[0]
            cid = qs.get('classId', [''])[0]
            raw = BGIMG_CACHE.get(cid)
            if raw:
                self._json(self._echo_mark(json.loads(raw), mark))
            else:
                self._json({'success': True, 'responseBody': '', 'curReqMark': mark})
            return

        # ---- share panel ----
        if path == '/front/share':
            raw = RAW_API.get('share')
            if raw:
                self._send_bytes(raw)
            else:
                self._json({'success': True, 'responseBody': ''})
            return

        # ---- other stubs ----
        if path in STUBS:
            body = STUBS[path]
            if path == '/meta-search':
                q = qs.get('q', [''])[0]
                self.send_response(302)
                self.send_header('Location', 'https://www.baidu.com/s?wd=' + q)
                self.end_headers()
                return
            self._json(self._echo_mark(body, qs.get('curReqMark', [''])[0]))
            return

        if path.startswith('/front/weather/'):
            self.send_response(204)
            self.end_headers()
            return

        super().do_GET()

    # ----------------------------------------------------------------- POST --
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ---- admin API ----
        if path == '/admin/api/login':
            data = self._body()
            admin = admin_db.verify_admin_login(data.get('username', ''), data.get('password', ''))
            if not admin:
                self._json({'success': False, 'message': '管理员账号或密码错误'}, status=401)
                return
            token = admin_db.create_admin_session(admin['username'])
            cookie = ('%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d'
                      % (admin_db.ADMIN_SESSION_COOKIE, token, admin_db.ADMIN_SESSION_TTL))
            self._json({'success': True, 'message': '登录成功', 'user': admin},
                       extra_headers={'Set-Cookie': cookie})
            return

        if path == '/admin/api/logout':
            token = admin_db.admin_session_from_headers(self.headers)
            admin_db.delete_admin_session(token)
            cookie = ('%s=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'
                      % admin_db.ADMIN_SESSION_COOKIE)
            self._json({'success': True}, extra_headers={'Set-Cookie': cookie})
            return

        if path == '/admin/api/change_password':
            admin = self._require_admin()
            if not admin:
                return
            data = self._body()
            result = admin_db.change_admin_password(
                admin['username'], data.get('old_password', ''), data.get('new_password', ''))
            self._json(result)
            return

        if path in ('/admin/api/save', '/admin/api/delete', '/admin/api/toggle'):
            if not self._require_admin():
                return
            data = self._body()
            kind = str(data.get('type', ''))
            if kind not in admin_db.TABLES:
                self._json({'success': False, 'message': '未知数据类型'}, status=400)
                return
            try:
                if path == '/admin/api/save':
                    rowid = data.get('id')
                    if rowid in (None, '', 0, '0'):
                        result = admin_db.insert_row(kind, data.get('fields') or {})
                    else:
                        result = admin_db.update_row(kind, rowid, data.get('fields') or {})
                elif path == '/admin/api/delete':
                    result = admin_db.delete_row(kind, data.get('id'))
                else:
                    result = admin_db.set_flag(kind, data.get('id'),
                                               data.get('field'), data.get('value'))
            except ValueError as e:
                result = {'success': False, 'message': str(e)}
            self._json(result)
            return

        if path == '/auth/register':
            data = self._body()
            username = str(data.get('username', '')).strip()
            password = str(data.get('password', ''))
            nickname = str(data.get('nickname', '')).strip()
            email = str(data.get('email', '')).strip()
            if len(username) < 3 or len(username) > 32:
                self._json({'success': False, 'message': '用户名需 3-32 个字符'})
                return
            if len(password) < 6:
                self._json({'success': False, 'message': '密码至少 6 位'})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO users (username, password_hash, nickname, email)
                             VALUES (?, ?, ?, ?)''',
                          (username, hash_password(password), nickname or username, email))
                conn.commit()
                uid = c.lastrowid
                self._json({'success': True, 'message': '注册成功',
                            'user': {'id': uid, 'username': username,
                                     'nickname': nickname or username, 'email': email}})
            except sqlite3.IntegrityError:
                self._json({'success': False, 'message': '用户名已存在'})
            finally:
                conn.close()
            return

        if path == '/auth/login':
            data = self._body()
            username = str(data.get('username', '')).strip()
            password = str(data.get('password', ''))
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = c.fetchone()
            if not row or not verify_password(password, row['password_hash']):
                conn.close()
                self._json({'success': False, 'message': '用户名或密码错误'})
                return
            token = secrets.token_urlsafe(32)
            now = int(time.time())
            c.execute('INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
                      (token, row['id'], now, now + SESSION_TTL))
            c.execute("UPDATE users SET last_login = datetime('now','localtime') WHERE id = ?", (row['id'],))
            conn.commit()
            conn.close()
            cookie = f'{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL}'
            self._json({'success': True, 'message': '登录成功', 'user': public_user(row)},
                       extra_headers={'Set-Cookie': cookie})
            return

        if path == '/auth/logout':
            token = session_token_from_headers(self.headers)
            if token:
                conn = sqlite3.connect(DB_PATH)
                conn.cursor().execute('DELETE FROM sessions WHERE token = ?', (token,))
                conn.commit()
                conn.close()
            cookie = f'{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'
            self._json({'success': True}, extra_headers={'Set-Cookie': cookie})
            return

        if path == '/auth/change_password':
            user = current_user(self.headers)
            if not user:
                self._json({'success': False, 'message': '请先登录'}, status=401)
                return
            data = self._body()
            old = str(data.get('old_password', ''))
            new = str(data.get('new_password', ''))
            if len(new) < 6:
                self._json({'success': False, 'message': '新密码至少 6 位'})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT password_hash FROM users WHERE id = ?', (user['id'],))
            row = c.fetchone()
            if not row or not verify_password(old, row[0]):
                conn.close()
                self._json({'success': False, 'message': '原密码错误'})
                return
            c.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                      (hash_password(new), user['id']))
            conn.commit()
            conn.close()
            self._json({'success': True, 'message': '密码已修改'})
            return

        # other POST endpoints fall back to GET logic (stubs tolerate POST)
        self.do_GET()

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == '__main__':
    init_db()
    # Auto-build the site SQLite DB on first run if it doesn't exist
    if not os.path.exists(SITE_DB):
        print('Building site_data.db from captured data (first run)...')
        import subprocess
        subprocess.run([sys.executable, os.path.join(ROOT, 'build_sitedb.py')], check=True)
    admin_db.ensure_site_schema()
    os.chdir(ROOT)
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Serving 51kim mirror at http://127.0.0.1:{PORT}/')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

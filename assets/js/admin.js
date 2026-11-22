(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);

  const LABELS = {
    categories: '分类标签',
    groups: '站点分组',
    sites: '站点条目',
    icons: '顶部图标',
    users: '注册用户',
  };
  const DESCS = {
    categories: '管理首页顶部的内网 / 外网分类标签',
    groups: '管理每个分类下的站点分组',
    sites: '管理导航站点：名称、网址、图标、排序、显示与启用状态',
    icons: '管理首页右上角的功能入口图标',
    users: '管理本地注册用户信息，支持重置密码与删除用户',
  };
  const FIELD_LABELS = {
    _rowid: 'ID',
    id: '标识',
    name: '名称',
    list_type: '列表类型',
    sort_order: '排序',
    enabled: '启用',
    visible: '显示',
    category_id: '分类 ID',
    group_key: '分组标识',
    group_name: '分组名称',
    url: '网址',
    icon: '图标路径',
    title: '标题',
    icon_cls: '图标样式类',
    hover_cls: '悬停样式类',
    menu_type: '菜单类型',
    custom_style: '自定义样式',
    username: '用户名',
    nickname: '昵称',
    email: '邮箱',
    created_at: '注册时间',
    last_login: '最后登录',
    password: '密码',
    old_password: '当前密码',
    new_password: '新密码',
    confirm_password: '确认密码',
  };

  const state = {
    kind: 'categories',
    columns: [],
    immutable: [],
    rows: [],
    counts: {},
    editingId: null,
    modalMode: 'record',
    options: { categories: [], groups: [] },
  };

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  async function api(path, options, allow401) {
    const opts = Object.assign({ credentials: 'same-origin' }, options || {});
    opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    const res = await fetch(path, opts);
    let data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (res.status === 401 && !allow401) {
      showLogin('登录已过期，请重新登录');
      throw new Error(data.message || '登录已过期');
    }
    if (!res.ok || data.success === false) {
      throw new Error(data.message || ('请求失败 HTTP ' + res.status));
    }
    return data;
  }

  function showLogin(message) {
    $('login-view').classList.remove('hidden');
    $('app-view').classList.add('hidden');
    $('modal').classList.add('hidden');
    if (message) $('login-msg').textContent = message;
  }

  function showApp(user) {
    $('login-view').classList.add('hidden');
    $('app-view').classList.remove('hidden');
    $('login-msg').textContent = '';
    $('who').textContent = '管理员：' + (user && user.username ? user.username : 'admin');
    loadOptions();
    loadTable();
  }

  function showNotice(message, error) {
    const el = $('notice');
    el.textContent = message;
    el.classList.toggle('error', !!error);
    el.classList.remove('hidden');
    clearTimeout(showNotice._timer);
    showNotice._timer = setTimeout(function () { el.classList.add('hidden'); }, 3000);
  }

  function renderStats(counts) {
    const keys = ['categories', 'groups', 'sites', 'icons', 'users'];
    $('stat-grid').innerHTML = keys.map(function (k) {
      return '<div class="stat"><div class="num">' + Number(counts[k] || 0) +
        '</div><div class="label">' + LABELS[k] + '</div></div>';
    }).join('');
    keys.forEach(function (k) {
      const badge = $('nav-' + k);
      if (badge) badge.textContent = counts[k] || 0;
    });
  }

  function setKind(kind) {
    if (!LABELS[kind]) return;
    state.kind = kind;
    document.querySelectorAll('.nav').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.kind === kind);
    });
    $('page-title').textContent = LABELS[kind];
    $('table-title').textContent = LABELS[kind];
    $('table-desc').textContent = DESCS[kind];
    $('search').value = '';
    loadTable();
  }

  async function loadOptions() {
    try {
      const [cats, groups] = await Promise.all([
        api('/admin/api/data?type=categories'),
        api('/admin/api/data?type=groups'),
      ]);
      state.options.categories = cats.rows;
      state.options.groups = groups.rows;
      ensureDatalists();
    } catch (e) {
      // Options are only a convenience; text input still works.
    }
  }

  function ensureDatalists() {
    [
      ['cat-options', state.options.categories.map(function (r) { return r.id; })],
      ['group-options', state.options.groups.map(function (r) { return r.group_key; })],
      ['menu-options', ['USER_CENTER', 'BG_CENTER', 'SHARE_WEBSITE', 'HELP_INFO', 'GOUP']],
    ].forEach(function (item) {
      let dl = document.getElementById(item[0]);
      if (!dl) {
        dl = document.createElement('datalist');
        dl.id = item[0];
        document.body.appendChild(dl);
      }
      dl.innerHTML = item[1].filter(Boolean).map(function (v) {
        return '<option value="' + esc(v) + '"></option>';
      }).join('');
    });
  }

  async function loadTable() {
    try {
      const data = await api('/admin/api/data?type=' + encodeURIComponent(state.kind));
      state.columns = data.columns;
      state.immutable = data.immutable || [];
      state.rows = data.rows;
      state.counts = data.counts;
      renderStats(data.counts);
      renderTable();
    } catch (e) {
      showNotice(e.message, true);
    }
  }

  function filteredRows() {
    const q = ($('search').value || '').trim().toLowerCase();
    if (!q) return state.rows;
    return state.rows.filter(function (row) {
      return state.columns.some(function (col) {
        return String(row[col] == null ? '' : row[col]).toLowerCase().indexOf(q) >= 0;
      });
    });
  }

  function flagCell(value) {
    if (value === 1 || value === '1') return '<span class="pill on">是</span>';
    return '<span class="pill off">否</span>';
  }

  function renderTable() {
    const cols = state.columns;
    $('table-head').innerHTML = '<tr>' + cols.map(function (c) {
      return '<th>' + esc(FIELD_LABELS[c] || c) + '</th>';
    }).join('') + '<th>操作</th></tr>';

    const rows = filteredRows();
    $('table-body').innerHTML = rows.map(function (row) {
      const cells = cols.map(function (c) {
        if (c === 'enabled' || c === 'visible') return '<td>' + flagCell(row[c]) + '</td>';
        return '<td><div class="cell-value" title="' + esc(row[c]) + '">' + esc(row[c]) + '</div></td>';
      }).join('');
      const id = esc(row._rowid);
      let actions = '<button class="btn mini" data-action="edit" data-id="' + id + '">编辑</button>';
      if (state.kind === 'users') {
        actions += '<button class="btn mini" data-action="resetpw" data-id="' + id + '">重置密码</button>';
      } else {
        const toggleEnabled = Number(row.enabled) ? 0 : 1;
        const toggleVisible = Number(row.visible) ? 0 : 1;
        actions += '<button class="btn mini" data-action="toggle" data-field="enabled" data-value="' + toggleEnabled + '" data-id="' + id + '">' +
          (Number(row.enabled) ? '停用' : '启用') + '</button>' +
          '<button class="btn mini" data-action="toggle" data-field="visible" data-value="' + toggleVisible + '" data-id="' + id + '">' +
          (Number(row.visible) ? '隐藏' : '显示') + '</button>';
      }
      actions += '<button class="btn mini danger" data-action="delete" data-id="' + id + '">删除</button>';
      actions = '<td><div class="actions">' + actions + '</div></td>';
      return '<tr>' + cells + actions + '</tr>';
    }).join('');

    $('table-foot').textContent = '显示 ' + rows.length + ' / ' + state.rows.length + ' 条记录（ID 为数据库内部行号）';
  }

  function fieldInput(col, row, editing) {
    const label = FIELD_LABELS[col] || col;
    const disabled = editing && state.immutable.indexOf(col) >= 0;
    const value = row && row[col] != null ? row[col] : '';
    let control;

    if (col === 'enabled' || col === 'visible') {
      control = '<select name="' + col + '"' + (disabled ? ' disabled' : '') + '>' +
        '<option value="1"' + (Number(value) ? ' selected' : '') + '>是</option>' +
        '<option value="0"' + (!Number(value) ? ' selected' : '') + '>否</option></select>';
    } else if (col === 'list_type') {
      control = '<select name="' + col + '"' + (disabled ? ' disabled' : '') + '>' +
        ['inner', 'outer'].map(function (v) {
          return '<option value="' + v + '"' + (value === v ? ' selected' : '') + '>' + v + '</option>';
        }).join('') + '</select>';
    } else {
      let type = 'text';
      let extra = '';
      if (col === 'sort_order') type = 'number';
      if (col === 'category_id') extra = ' list="cat-options"';
      if (col === 'group_key') extra = ' list="group-options"';
      if (col === 'menu_type') extra = ' list="menu-options"';
      if (col === 'password' || col === 'old_password' || col === 'new_password' || col === 'confirm_password') {
        type = 'password';
        const placeholder = col === 'old_password' ? '请输入当前密码'
          : col === 'confirm_password' ? '再次输入新密码' : '至少 6 位，留空表示不修改';
        extra = ' placeholder="' + placeholder + '" autocomplete="new-password"';
      }
      control = '<input type="' + type + '" name="' + col + '" value="' + esc(value) + '"' +
        extra + (disabled ? ' disabled' : '') + '>';
    }
    return '<div><label>' + esc(label) + (disabled ? '（不可修改）' : '') + '</label>' + control + '</div>';
  }

  function openEditor(row) {
    const editing = !!row;
    state.modalMode = 'record';
    state.editingId = editing ? row._rowid : null;
    $('modal-msg').textContent = '';
    $('modal-title').textContent = (editing ? '编辑' : '新增') + LABELS[state.kind];
    const blank = {};
    if (!editing) {
      const maxSort = state.rows.reduce(function (m, r) { return Math.max(m, Number(r.sort_order) || 0); }, -1);
      blank.sort_order = maxSort + 1;
      blank.enabled = 1;
      blank.visible = 1;
      if (state.kind === 'categories') blank.list_type = 'inner';
      if (state.kind === 'icons') blank.menu_type = 'HELP_INFO';
    }
    const source = row || blank;
    const cols = state.columns.slice();
    if (state.kind === 'users') cols.push('password', 'confirm_password');
    $('form-fields').innerHTML = cols.map(function (col) {
      return fieldInput(col, source, editing);
    }).join('');
    $('modal').classList.remove('hidden');
    ensureDatalists();
  }

  function openPasswordModal(mode, row) {
    state.modalMode = mode;
    state.editingId = row ? row._rowid : null;
    $('modal-msg').textContent = '';
    if (mode === 'admin_password') {
      $('modal-title').textContent = '修改管理员密码';
      $('form-fields').innerHTML = ['old_password', 'new_password', 'confirm_password'].map(function (c) {
        return fieldInput(c, {}, false);
      }).join('');
    } else {
      $('modal-title').textContent = '重置用户密码';
      $('form-fields').innerHTML = ['password', 'confirm_password'].map(function (c) {
        return fieldInput(c, {}, false);
      }).join('');
    }
    $('modal').classList.remove('hidden');
  }

  function closeEditor() {
    $('modal').classList.add('hidden');
    state.editingId = null;
    state.modalMode = 'record';
  }

  async function saveEditor(event) {
    event.preventDefault();
    const fields = {};
    new FormData($('edit-form')).forEach(function (value, key) { fields[key] = value; });
    $('modal-msg').textContent = '';

    if (state.modalMode === 'admin_password' || state.modalMode === 'resetpw' || state.kind === 'users') {
      if (fields.new_password && fields.new_password !== fields.confirm_password) {
        $('modal-msg').textContent = '两次输入的新密码不一致';
        return;
      }
      if (fields.password && fields.password !== fields.confirm_password) {
        $('modal-msg').textContent = '两次输入的密码不一致';
        return;
      }
    }

    try {
      let result;
      if (state.modalMode === 'admin_password') {
        result = await api('/admin/api/change_password', {
          method: 'POST',
          body: JSON.stringify({
            old_password: fields.old_password,
            new_password: fields.new_password,
          }),
        });
      } else if (state.modalMode === 'resetpw') {
        delete fields.confirm_password;
        result = await api('/admin/api/save', {
          method: 'POST',
          body: JSON.stringify({ type: 'users', id: state.editingId, fields: fields }),
        });
      } else {
        if (state.kind === 'users') {
          delete fields.confirm_password;
          if (!fields.password) delete fields.password;
        }
        result = await api('/admin/api/save', {
          method: 'POST',
          body: JSON.stringify({
            type: state.kind,
            id: state.editingId,
            fields: fields,
          }),
        });
      }
      closeEditor();
      showNotice(result.message || '已保存');
      await loadTable();
    } catch (e) {
      $('modal-msg').textContent = e.message;
    }
  }

  async function handleTableAction(event) {
    const btn = event.target.closest('button[data-action]');
    if (!btn) return;
    const action = btn.dataset.action;
    const id = btn.dataset.id;
    const row = state.rows.find(function (r) { return String(r._rowid) === String(id); });
    if (!row) return;

    if (action === 'edit') {
      openEditor(row);
      return;
    }
    if (action === 'resetpw') {
      openPasswordModal('resetpw', row);
      return;
    }
    if (action === 'delete') {
      if (!confirm('确认删除这条记录？此操作不可恢复。')) return;
      try {
        const result = await api('/admin/api/delete', {
          method: 'POST', body: JSON.stringify({ type: state.kind, id: id }),
        });
        showNotice(result.message || '已删除');
        await loadTable();
      } catch (e) { showNotice(e.message, true); }
      return;
    }
    if (action === 'toggle') {
      try {
        const result = await api('/admin/api/toggle', {
          method: 'POST',
          body: JSON.stringify({
            type: state.kind, id: id, field: btn.dataset.field, value: btn.dataset.value,
          }),
        });
        showNotice(result.message || '已更新');
        await loadTable();
      } catch (e) { showNotice(e.message, true); }
    }
  }

  $('login-form').addEventListener('submit', async function (event) {
    event.preventDefault();
    $('login-msg').textContent = '登录中…';
    try {
      const result = await api('/admin/api/login', {
        method: 'POST',
        body: JSON.stringify({
          username: $('admin-user').value.trim(),
          password: $('admin-pass').value,
        }),
      }, true);
      showApp(result.user);
    } catch (e) {
      $('login-msg').textContent = e.message;
    }
  });

  $('logout-btn').addEventListener('click', async function () {
    try { await api('/admin/api/logout', { method: 'POST' }); } catch (e) { /* ignore */ }
    showLogin();
  });

  document.querySelectorAll('.nav[data-kind]').forEach(function (btn) {
    btn.addEventListener('click', function () { setKind(btn.dataset.kind); });
  });
  $('admin-pw-btn').addEventListener('click', function () { openPasswordModal('admin_password', null); });
  $('search').addEventListener('input', renderTable);
  $('refresh-btn').addEventListener('click', loadTable);
  $('add-btn').addEventListener('click', function () { openEditor(null); });
  $('modal-close').addEventListener('click', closeEditor);
  $('cancel-btn').addEventListener('click', closeEditor);
  $('edit-form').addEventListener('submit', saveEditor);
  $('table-body').addEventListener('click', handleTableAction);

  api('/admin/api/session').then(function (session) {
    if (session.authenticated) showApp(session.user);
    else showLogin();
  }).catch(function () { showLogin(); });
})();

/* Local SQLite-backed authentication UI for the 51kim mirror.
   Intercepts clicks on the "个人中心" header icon and replaces the original
   third-party OAuth login panel with a local username/password login. */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  var overlay, body, currentUser = null, mode = 'login';

  function api(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    if (options.json) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.json);
    }
    return fetch(url, options).then(function (r) { return r.json(); });
  }

  function buildUI() {
    overlay = document.createElement('div');
    overlay.className = 'la-overlay';
    overlay.innerHTML =
      '<div class="la-panel" onclick="event.stopPropagation()">' +
        '<div class="la-head"><h3>个人中心</h3><span class="la-close" title="关闭">×</span></div>' +
        '<div class="la-body"></div>' +
      '</div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) close();
    });
    overlay.querySelector('.la-close').addEventListener('click', close);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay.classList.contains('la-open')) close();
    });
  }

  function setMsg(text, kind) {
    var m = body.querySelector('.la-msg');
    if (m) { m.textContent = text || ''; m.className = 'la-msg ' + (kind || ''); }
  }

  function renderLogin() {
    mode = 'login';
    body.innerHTML =
      '<div class="la-tabs">' +
        '<div class="la-tab active" data-mode="login">登录</div>' +
        '<div class="la-tab" data-mode="register">注册</div>' +
      '</div>' +
      '<div class="la-field"><label>用户名</label><input class="la-user-input" autocomplete="username" placeholder="请输入用户名"></div>' +
      '<div class="la-field"><label>密码</label><input class="la-pass-input" type="password" autocomplete="current-password" placeholder="请输入密码"></div>' +
      '<div class="la-msg"></div>' +
      '<button class="la-btn la-submit">登 录</button>' +
      '<div class="la-hint">本地账号 · 数据保存在 SQLite 数据库<br>首次使用请先注册 · <a href="/admin" target="_blank" style="color:#6a6fd6">后台管理</a></div>';

    body.querySelectorAll('.la-tab').forEach(function (t) {
      t.addEventListener('click', function () {
        if (t.dataset.mode === 'register') renderRegister();
      });
    });
    body.querySelector('.la-submit').addEventListener('click', doLogin);
    body.addEventListener('keydown', enterSubmit);
    var u = body.querySelector('.la-user-input');
    if (u) u.focus();
  }

  function renderRegister() {
    mode = 'register';
    body.innerHTML =
      '<div class="la-tabs">' +
        '<div class="la-tab" data-mode="login">登录</div>' +
        '<div class="la-tab active" data-mode="register">注册</div>' +
      '</div>' +
      '<div class="la-field"><label>用户名</label><input class="la-user-input" autocomplete="username" placeholder="3-32 个字符"></div>' +
      '<div class="la-field"><label>昵称（可选）</label><input class="la-nick-input" placeholder="显示名称"></div>' +
      '<div class="la-field"><label>邮箱（可选）</label><input class="la-email-input" autocomplete="email" placeholder="邮箱地址"></div>' +
      '<div class="la-field"><label>密码</label><input class="la-pass-input" type="password" autocomplete="new-password" placeholder="至少 6 位"></div>' +
      '<div class="la-field"><label>确认密码</label><input class="la-pass2-input" type="password" autocomplete="new-password" placeholder="再次输入密码"></div>' +
      '<div class="la-msg"></div>' +
      '<button class="la-btn la-submit">注 册</button>' +
      '<div class="la-hint">已有账号？<span class="la-tab" style="display:inline;color:#6a6fd6" id="la-to-login">返回登录</span></div>';

    body.querySelectorAll('.la-tab[data-mode]').forEach(function (t) {
      t.addEventListener('click', function () {
        if (t.dataset.mode === 'login') renderLogin();
      });
    });
    body.querySelector('#la-to-login').addEventListener('click', renderLogin);
    body.querySelector('.la-submit').addEventListener('click', doRegister);
    body.addEventListener('keydown', enterSubmit);
  }

  function renderUser() {
    var u = currentUser;
    var initial = (u.nickname || u.username).charAt(0).toUpperCase();
    body.innerHTML =
      '<div class="la-user">' +
        '<div class="la-avatar">' + escapeHtml(initial) + '</div>' +
        '<div class="la-nick">' + escapeHtml(u.nickname || u.username) + '</div>' +
        '<div class="la-uname">@' + escapeHtml(u.username) + (u.email ? ' · ' + escapeHtml(u.email) : '') + '</div>' +
        '<div class="la-meta">已登录 · 本地账号</div>' +
      '</div>' +
      '<div class="la-msg"></div>' +
      '<div class="la-actions">' +
        '<button class="la-btn ghost la-changepw">修改密码</button>' +
        '<a class="la-btn ghost" href="/admin" target="_blank" style="text-decoration:none;text-align:center;line-height:1.8">后台管理</a>' +
        '<button class="la-btn la-logout">退出登录</button>' +
      '</div>' +
      '<div class="la-pw-box">' +
        '<div class="la-field"><label>原密码</label><input class="la-oldpw" type="password" placeholder="请输入原密码"></div>' +
        '<div class="la-field"><label>新密码</label><input class="la-newpw" type="password" placeholder="至少 6 位"></div>' +
        '<button class="la-btn la-pw-submit">确认修改</button>' +
      '</div>';
    body.querySelector('.la-logout').addEventListener('click', doLogout);
    body.querySelector('.la-changepw').addEventListener('click', function () {
      var box = body.querySelector('.la-pw-box');
      box.style.display = box.style.display === 'block' ? 'none' : 'block';
    });
    body.querySelector('.la-pw-submit').addEventListener('click', doChangePw);
  }

  function enterSubmit(e) { if (e.key === 'Enter') { var b = body.querySelector('.la-submit'); if (b) b.click(); } }

  function doLogin() {
    var username = body.querySelector('.la-user-input').value.trim();
    var password = body.querySelector('.la-pass-input').value;
    if (!username || !password) { setMsg('请输入用户名和密码', 'err'); return; }
    setMsg('登录中...');
    api('/auth/login', { method: 'POST', json: { username: username, password: password } })
      .then(function (res) {
        if (res.success) { currentUser = res.user; setMsg('登录成功', 'ok'); renderUser(); }
        else setMsg(res.message || '登录失败', 'err');
      })
      .catch(function () { setMsg('网络错误，请重试', 'err'); });
  }

  function doRegister() {
    var username = body.querySelector('.la-user-input').value.trim();
    var nickname = body.querySelector('.la-nick-input').value.trim();
    var email = body.querySelector('.la-email-input').value.trim();
    var password = body.querySelector('.la-pass-input').value;
    var password2 = body.querySelector('.la-pass2-input').value;
    if (!username || !password) { setMsg('请输入用户名和密码', 'err'); return; }
    if (password !== password2) { setMsg('两次密码不一致', 'err'); return; }
    setMsg('注册中...');
    api('/auth/register', { method: 'POST', json: { username: username, nickname: nickname, email: email, password: password } })
      .then(function (res) {
        if (res.success) {
          currentUser = res.user;
          setMsg('注册成功', 'ok');
          return api('/auth/login', { method: 'POST', json: { username: username, password: password } })
            .then(function (lr) { if (lr.success) currentUser = lr.user; renderUser(); });
        }
        setMsg(res.message || '注册失败', 'err');
      })
      .catch(function () { setMsg('网络错误，请重试', 'err'); });
  }

  function doLogout() {
    api('/auth/logout', { method: 'POST' }).then(function () {
      currentUser = null; renderLogin();
    });
  }

  function doChangePw() {
    var oldPw = body.querySelector('.la-oldpw').value;
    var newPw = body.querySelector('.la-newpw').value;
    if (!oldPw || !newPw) { setMsg('请填写原密码和新密码', 'err'); return; }
    api('/auth/change_password', { method: 'POST', json: { old_password: oldPw, new_password: newPw } })
      .then(function (res) {
        setMsg(res.message || (res.success ? '修改成功' : '修改失败'), res.success ? 'ok' : 'err');
        if (res.success) {
          body.querySelector('.la-oldpw').value = '';
          body.querySelector('.la-newpw').value = '';
          body.querySelector('.la-pw-box').style.display = 'none';
        }
      });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function open() {
    if (currentUser) renderUser(); else renderLogin();
    overlay.classList.add('la-open');
  }
  function close() { overlay.classList.remove('la-open'); }

  ready(function () {
    buildUI();
    body = overlay.querySelector('.la-body');

    // Intercept clicks on the 个人中心 header icon (capture phase, stop the
    // original OAuth panel from opening).
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (t.closest && t.closest('.user-center-icon, .user-center-icon-hover')) {
        e.stopPropagation();
        e.preventDefault();
        open();
      }
    }, true);

    // Restore session on load
    api('/auth/me').then(function (res) {
      if (res.success && res.user) currentUser = res.user;
    }).catch(function () {});
  });
})();

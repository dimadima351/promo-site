/*!
 * card-widget.js — ТИМЧАСОВА віджет-картка клієнта.
 * Підключення:  <script src="card-widget.js" defer></script>  (перед </body>)
 * Видалення:    просто прибери цей рядок (і файл). Більше нічого чистити не треба.
 * Опційно очистити дані на пристрої: window.cardWidgetRemove(true)
 */
(function () {
  'use strict';
  if (window.__cardWidget) return;
  window.__cardWidget = true;

  var LS_KEY = 'cw_rec_v1';
  var DB_NAME = 'cw_keys', STORE = 'k', KEY_ID = 'main';
  var enc = new TextEncoder(), dec = new TextDecoder();

  /* ---------- Стилі (тільки смартфон) ---------- */
  var css = '\
#cw-btn,#cw-ov{display:none}\
@media (max-width:768px){\
#cw-btn{display:flex;position:fixed;right:14px;bottom:14px;width:52px;height:52px;border:0;border-radius:10px;\
background:#111;color:#fff;align-items:center;justify-content:center;z-index:2147483000;box-shadow:0 4px 14px rgba(0,0,0,.35);padding:0}\
#cw-btn svg{width:30px;height:30px}\
#cw-ov.cw-open{display:flex;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:2147483001;align-items:center;justify-content:center;padding:16px}\
}\
#cw-box{background:#fff;color:#111;width:100%;max-width:340px;border-radius:16px;padding:20px;font:16px/1.4 system-ui,Arial,sans-serif;position:relative;box-sizing:border-box}\
#cw-box h3{margin:0 0 12px;font-size:18px}\
#cw-box input{width:100%;box-sizing:border-box;padding:12px;margin:0 0 10px;border:1px solid #bbb;border-radius:8px;font-size:16px}\
#cw-box .cw-go{width:100%;padding:12px;border:0;border-radius:8px;background:#111;color:#fff;font-size:16px}\
#cw-x{position:absolute;top:6px;right:10px;border:0;background:none;font-size:28px;line-height:1;color:#555}\
#cw-err{color:#c00;font-size:14px;min-height:18px;margin:0 0 6px}\
#cw-card{text-align:center}\
#cw-card .cw-n{font-weight:600;font-size:18px;margin-top:10px}\
#cw-card .cw-p{color:#444;margin:2px 0 8px}\
#cw-card svg{width:100%;height:auto;display:block}\
#cw-dev{margin-top:6px;font-size:8px;line-height:1}#cw-dev a{color:#aaa;text-decoration:none}\
#cw-del{margin-top:12px;border:0;background:none;color:#888;font-size:12px;text-decoration:underline}';

  var style = document.createElement('style');
  style.id = 'cw-style';
  style.textContent = css;
  document.head.appendChild(style);

  /* ---------- DOM ---------- */
  var btn = document.createElement('button');
  btn.id = 'cw-btn';
  btn.type = 'button';
  btn.setAttribute('aria-label', 'Моя картка');
  btn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h8v8H3V3zm2 2v4h4V5H5zm8-2h8v8h-8V3zm2 2v4h4V5h-4zM3 13h8v8H3v-8zm2 2v4h4v-4H5zm10-2h2v2h-2v-2zm-2 2h2v2h-2v-2zm4 0h2v2h-2v-2zm-2 2h2v2h-2v-2zm2 2h2v2h-2v-2zm-4 0h2v2h-2v-2zm2-6h2v2h-2v-2zm4 0h2v2h-2v-2z"/></svg>';
  var ov = document.createElement('div');
  ov.id = 'cw-ov';
  ov.innerHTML = '<div id="cw-box"><button id="cw-x" type="button" aria-label="Закрити">&times;</button><div id="cw-body"></div></div>';
  document.body.appendChild(btn);
  document.body.appendChild(ov);
  var body = ov.querySelector('#cw-body');

  var SHOW_SECONDS = 10; // кнопка видима стільки секунд після завантаження сторінки (0 = завжди)
  if (SHOW_SECONDS > 0 && !isDev()) {
    setTimeout(function () { btn.style.display = 'none'; }, SHOW_SECONDS * 1000);
  }
  btn.addEventListener('click', open);
  ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
  ov.querySelector('#cw-x').addEventListener('click', close);

  function close() { ov.classList.remove('cw-open'); body.innerHTML = ''; }

  async function open() {
    ov.classList.add('cw-open');
    var rec = null;
    try { rec = await loadRecord(); } catch (e) { rec = null; }
    rec ? showCard(rec) : showForm();
  }

  /* ---------- Захищене зберігання ----------
     Дані шифруються AES-GCM. Ключ — non-extractable CryptoKey в IndexedDB,
     тому скопіювавши localStorage, дані не прочитати. Потрібен HTTPS. */
  function idb() {
    return new Promise(function (res, rej) {
      var r = indexedDB.open(DB_NAME, 1);
      r.onupgradeneeded = function () { r.result.createObjectStore(STORE); };
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error); };
    });
  }
  async function getKey(create) {
    var db = await idb();
    var key = await new Promise(function (res) {
      var q = db.transaction(STORE).objectStore(STORE).get(KEY_ID);
      q.onsuccess = function () { res(q.result); };
      q.onerror = function () { res(null); };
    });
    if (!key && create) {
      key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
      await new Promise(function (res, rej) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(key, KEY_ID);
        tx.oncomplete = res; tx.onerror = function () { rej(tx.error); };
      });
    }
    db.close();
    return key || null;
  }
  function b64(buf) { return btoa(String.fromCharCode.apply(null, new Uint8Array(buf))); }
  function unb64(s) { return Uint8Array.from(atob(s), function (c) { return c.charCodeAt(0); }); }

  async function saveRecord(rec) {
    var key = await getKey(true);
    var iv = crypto.getRandomValues(new Uint8Array(12));
    var ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, enc.encode(JSON.stringify(rec)));
    localStorage.setItem(LS_KEY, b64(iv) + '.' + b64(ct));
  }
  async function loadRecord() {
    var raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    var key = await getKey(false);
    if (!key) return null;
    var p = raw.split('.');
    var pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(p[0]) }, key, unb64(p[1]));
    return JSON.parse(dec.decode(pt));
  }

  /* ---------- Реєстрація ---------- */
  function fmtPhone(v) {
    var d = v.replace(/\D/g, '').slice(0, 10);
    var o = '';
    if (d.length) o = '(' + d.slice(0, 3);
    if (d.length >= 3) o += ')';
    if (d.length > 3) o += '-' + d.slice(3, 6);
    if (d.length > 6) o += '-' + d.slice(6, 8);
    if (d.length > 8) o += '-' + d.slice(8, 10);
    return o;
  }
  function genCard() {
    var a = new Uint32Array(10), s = '2299';
    crypto.getRandomValues(a);
    for (var i = 0; i < 10; i++) s += a[i] % 10;
    return s; // 2299 + 10 випадкових цифр = 14 цифр
  }

  function showForm() {
    body.innerHTML = '<h3>Реєстрація картки</h3>\
<input id="cw-name" type="text" placeholder="Ім\'я" autocomplete="name">\
<input id="cw-phone" type="tel" inputmode="numeric" placeholder="(096)-892-27-59" autocomplete="tel">\
<p id="cw-err"></p><button class="cw-go" type="button">Отримати картку</button>';
    var ph = body.querySelector('#cw-phone');
    ph.addEventListener('input', function () { ph.value = fmtPhone(ph.value); });
    body.querySelector('.cw-go').addEventListener('click', async function () {
      var name = body.querySelector('#cw-name').value.trim();
      var phone = ph.value;
      var err = body.querySelector('#cw-err');
      if (name.length < 2) { err.textContent = 'Введіть ім\'я'; return; }
      if (!/^\(\d{3}\)-\d{3}-\d{2}-\d{2}$/.test(phone)) { err.textContent = 'Телефон у форматі (096)-892-27-59'; return; }
      if (!window.crypto || !crypto.subtle || !window.indexedDB) { err.textContent = 'Потрібне безпечне з\'єднання (HTTPS)'; return; }
      var rec = { name: name, phone: phone, card: genCard() };
      try { await saveRecord(rec); } catch (e) { err.textContent = 'Не вдалося зберегти дані'; return; }
      showCard(rec);
    });
  }

  /* ---------- Картка + штрихкод ---------- */
  function showCard(rec) {
    body.innerHTML = '<div id="cw-card">' + (isDev() ? '<div class="cw-num" style="font:600 18px monospace;letter-spacing:1px;margin-bottom:6px"></div>' : '') + barcodeSVG(rec.card) +
      '<div class="cw-n"></div><div class="cw-p"></div>' +
      '<button id="cw-del" type="button">Видалити картку з цього пристрою</button></div>';
    var nm = body.querySelector('.cw-num');
    if (nm) nm.textContent = rec.card;
    body.querySelector('.cw-n').textContent = rec.name;   // textContent — без XSS
    body.querySelector('.cw-p').textContent = rec.phone;
    body.querySelector('#cw-del').addEventListener('click', function () {
      if (confirm('Видалити картку з цього пристрою?')) { wipe(); close(); }
    });
    if (isDev()) {
      var d = document.createElement('div');
      d.id = 'cw-dev';
      d.innerHTML = '<a href="#" id="cw-dev-a">змінити унікальний №</a>';
      body.querySelector('#cw-card').appendChild(d);
      d.querySelector('#cw-dev-a').addEventListener('click', function (e) {
        e.preventDefault();
        devChange(rec);
      });
    }
  }

  /* ---------- Режим розробника (тільки з ?cwdev=1 або #cwdev в адресі) ---------- */
  function isDev() {
    return /(^|[?&#])cwdev(=1|\b)/.test(location.search + location.hash);
  }
  function devChange(rec) {
    var v = prompt('Новий номер картки (будь-які цифри, без обмежень).\nПорожнє поле — згенерується випадковий:', rec.card);
    if (v === null) return;
    v = v.replace(/[^\x20-\x7E]/g, '').trim();
    if (v === '') v = genCard();
    rec.card = v;
    saveRecord(rec).then(function () { showCard(rec); }, function () { alert('Не вдалося зберегти'); });
  }

  /* ---------- Code 128, набір C (пари цифр) ---------- */
  var P = '212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112'.split(' ');

  function barcodeSVG(text) {
    var vals, sum;
    if (/^\d+$/.test(text) && text.length % 2 === 0) {
      vals = [105]; sum = 105;
      for (var i = 0; i < text.length; i += 2) {
        var v = parseInt(text.substr(i, 2), 10);
        vals.push(v);
        sum += v * (i / 2 + 1);
      }
    } else {
      vals = [104]; sum = 104;
      for (var k = 0; k < text.length; k++) {
        var c = text.charCodeAt(k) - 32;
        if (c < 0 || c > 94) c = 0;
        vals.push(c);
        sum += c * (k + 1);
      }
    }
    vals.push(sum % 103, 106);
    var x = 10, rects = '';
    vals.forEach(function (v) {
      var pat = P[v];
      for (var j = 0; j < pat.length; j++) {
        var w = +pat[j];
        if (j % 2 === 0) rects += '<rect x="' + x + '" y="0" width="' + w + '" height="90"/>';
        x += w;
      }
    });
    var total = x + 10;
    return '<svg viewBox="0 0 ' + total + ' 90" preserveAspectRatio="none" shape-rendering="crispEdges" style="background:#fff" fill="#000">' + rects + '</svg>';
  }

  /* ---------- Видалення віджета ---------- */
  function wipe() {
    try { localStorage.removeItem(LS_KEY); } catch (e) {}
    try { indexedDB.deleteDatabase(DB_NAME); } catch (e) {}
  }
  window.cardWidgetRemove = function (clearData) {
    if (clearData) wipe();
    [btn, ov, style].forEach(function (n) { n && n.parentNode && n.parentNode.removeChild(n); });
    delete window.cardWidgetRemove;
    window.__cardWidget = false;
  };
})();
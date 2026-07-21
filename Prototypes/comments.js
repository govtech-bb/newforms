/* ============================================================================
   GovBB prototype dev tools — Comments (PROTOTYPE REVIEW TOOL)
   ----------------------------------------------------------------------------
   Drop-in, self-contained. Add  <script src="comments.js" defer></script>
   before </body> on ANY prototype page (form flow, calculator, directory,
   content page, start/entry). No framework, no dependencies.

   Reviewers SELECT text on the page and leave a threaded comment anchored to
   that text (highlighted in place). The side panel lists every thread with
   replies, Resolve / Reopen, and a "show resolved" toggle. "Export all"
   downloads every page's comments as one Markdown file for a ticket or email.

   STORAGE: browser localStorage only, with an in-memory fallback for private
   browsing — comments are per-reviewer, per-browser, and never leave the
   machine. No backend, no keys, nothing shared. This is a review aid, never a
   shipped feature — don't present saved comments as service content.

   DEV-ONLY: this tool has its OWN gate, separate from auto-fill. It appears
   only when the URL carries ?comment (or ?comments), or the hash contains
   "comment" (#comment / #comments). Nothing else enables it — not ?dev, not
   localhost, not file:// — so a reviewer link can turn comments on without
   turning auto-fill on. Real users (no param) never see it.
   ============================================================================ */
(function () {
  "use strict";

  /* ---- dev gate: comments tool only, via ?comment / #comment ---- */
  var showComments =
    /[?&]comments?\b/.test(location.search) ||
    location.hash.indexOf('comment') !== -1;
  if (!showComments) return;

  var CFG = {
    root: '#main, main, #app',        // only text inside here is commentable
    prefix: 'govbb-comments::',
    authorKey: 'govbb-comments-author'
  };

  /* ---- page identity: URL path + visible H1 (so single-page framework flows
     scope by rendered step, multi-file prototypes scope by file) ---- */
  function currentHeading() {
    var root = document.querySelector('#app') || document;
    var h = root.querySelector('h1');
    return (h && h.textContent.trim()) || (document.title || '').trim() || 'Untitled page';
  }
  function pageKey() { return location.pathname + '::' + currentHeading(); }

  /* ---- storage: localStorage with in-memory fallback ---- */
  var mem = {};
  var LS = (function () {
    try { var t = CFG.prefix + '__t'; localStorage.setItem(t, '1'); localStorage.removeItem(t); return localStorage; }
    catch (e) { return null; }
  })();
  function getItem(k) { return LS ? LS.getItem(k) : (k in mem ? mem[k] : null); }
  function setItem(k, v) { if (LS) { try { LS.setItem(k, v); } catch (e) { mem[k] = v; } } else { mem[k] = v; } }
  function keyList() { if (LS) { var a = []; for (var i = 0; i < LS.length; i++) a.push(LS.key(i)); return a; } return Object.keys(mem); }
  function load(key) { try { return JSON.parse(getItem(CFG.prefix + key)) || []; } catch (e) { return []; } }
  function save(key, list) { setItem(CFG.prefix + key, JSON.stringify(list)); }
  function allKeys() {
    return keyList()
      .filter(function (k) { return k && k.indexOf(CFG.prefix) === 0 && k !== CFG.prefix + '__t'; })
      .map(function (k) { return k.slice(CFG.prefix.length); });
  }

  /* ---- author (inline, no blocking prompt) ---- */
  function getAuthor() { return getItem(CFG.authorKey) || ''; }

  /* ---- misc helpers ---- */
  var uid = function () { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); };
  function when(ts) { var s = (Date.now() - ts) / 1000; if (s < 60) return 'just now'; if (s < 3600) return Math.floor(s / 60) + 'm ago'; if (s < 86400) return Math.floor(s / 3600) + 'h ago'; return new Date(ts).toLocaleDateString(); }
  function esc(t) { var d = document.createElement('div'); d.textContent = (t == null ? '' : t); return d.innerHTML; }
  function rootEl() { return document.querySelector(CFG.root) || document.body; }

  /* ---- anchoring (W3C text-quote style) ---- */
  function textNodes(root) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (n.parentElement && n.parentElement.closest('[data-gcmt]')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var out = [], n; while ((n = w.nextNode())) out.push(n); return out;
  }
  function buildIndex(root) {
    var nodes = textNodes(root), full = '', map = [];
    nodes.forEach(function (node) { map.push({ node: node, start: full.length, end: full.length + node.nodeValue.length }); full += node.nodeValue; });
    return { full: full, map: map };
  }
  function locate(thread) {
    var idx = -1, ix = buildIndex(rootEl());
    if (thread.prefix || thread.suffix) {
      var probe = (thread.prefix || '') + thread.quote + (thread.suffix || ''), p = ix.full.indexOf(probe);
      if (p >= 0) idx = p + (thread.prefix || '').length;
    }
    if (idx < 0) idx = ix.full.indexOf(thread.quote);
    if (idx < 0) return null;
    return { start: idx, end: idx + thread.quote.length, map: ix.map };
  }
  function highlight(thread) {
    var loc = locate(thread); if (!loc) return false;
    loc.map.forEach(function (seg) {
      if (seg.end <= loc.start || seg.start >= loc.end) return;
      var a = Math.max(loc.start, seg.start) - seg.start, b = Math.min(loc.end, seg.end) - seg.start;
      var r = document.createRange();
      try { r.setStart(seg.node, a); r.setEnd(seg.node, b); } catch (e) { return; }
      var m = document.createElement('mark');
      m.className = 'gcmt-hl'; m.setAttribute('data-gcmt', 'hl'); m.dataset.thread = thread.id;
      if (thread.resolved) m.dataset.resolved = '1';
      m.addEventListener('click', function (e) { e.stopPropagation(); openPanel(); focusThread(thread.id); });
      try { r.surroundContents(m); } catch (e) { /* spans a block boundary — skip */ }
    });
    return true;
  }
  function clearHighlights() {
    var marks = document.querySelectorAll('mark.gcmt-hl');
    for (var i = 0; i < marks.length; i++) {
      var m = marks[i], p = m.parentNode;
      while (m.firstChild) p.insertBefore(m.firstChild, m);
      p.removeChild(m); p.normalize();
    }
  }

  /* ---- state ---- */
  var threads = [], showResolved = false;
  function refresh() {
    threads = load(pageKey());
    clearHighlights();
    threads.forEach(function (t) { if (!t.resolved || showResolved) highlight(t); });
    renderPanel();
    renderToggle();
  }

  /* ---- export as Markdown (all pages) ---- */
  function exportAll() {
    var keys = allKeys(), any = false;
    var lines = ['# Prototype review comments', '', 'Exported ' + new Date().toLocaleString(), ''];
    keys.forEach(function (k) {
      var list = load(k); if (!list.length) return; any = true;
      lines.push('## ' + (k.split('::').slice(1).join('::') || k));
      lines.push('_' + k.split('::')[0] + '_', '');
      list.forEach(function (t) {
        lines.push('> ' + t.quote.replace(/\n/g, ' '));
        var who = t.author ? '**' + t.author + '**' : '_anonymous_';
        lines.push('- ' + who + ' · ' + new Date(t.createdAt).toLocaleString() + (t.resolved ? ' · _resolved_' : ''));
        t.text.split('\n').forEach(function (x) { lines.push('  ' + x); });
        (t.replies || []).forEach(function (r) {
          lines.push('  - ↳ ' + (r.author ? '**' + r.author + '**' : '_anonymous_') + ' · ' + new Date(r.createdAt).toLocaleString());
          r.text.split('\n').forEach(function (x) { lines.push('    ' + x); });
        });
        lines.push('');
      });
    });
    if (!any) return;
    var blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'prototype-comments.md';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  /* ---- UI ---- */
  var toggleBtn, panel, listEl, authorInput, resolvedChk, hint, selBtn, composer;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    e.setAttribute('data-gcmt', 'ui');
    return e;
  }

  function buildUI() {
    var css = document.createElement('style');
    css.setAttribute('data-gcmt', 'style');
    css.textContent =
      '[data-gcmt]{box-sizing:border-box;font-family:"Figtree",system-ui,arial,sans-serif}' +
      'mark.gcmt-hl{background:#fff3c4;border-bottom:2px solid #ffc726;cursor:pointer;padding:0 1px}' +
      'mark.gcmt-hl[data-resolved]{background:#eef0f2;border-bottom-color:#b1b4b6}' +
      'mark.gcmt-hl.gcmt-flash{animation:gcmtFlash 1.2s ease}' +
      '@keyframes gcmtFlash{0%,100%{background:#fff3c4}50%{background:#ffd94d}}' +
      '.gcmt-toggle{position:fixed;left:16px;bottom:16px;z-index:2147483000;background:#0e5f64;color:#fff;border:0;border-radius:24px;padding:10px 16px;font-size:15px;font-weight:700;cursor:pointer;box-shadow:0 6px 24px rgba(11,28,75,.22),inset 0 1px 0 rgba(255,255,255,.7)}' +
      '.gcmt-toggle:hover{background:#0a4549}.gcmt-toggle:focus-visible{outline:3px solid #ffbf47;outline-offset:2px}' +
      '.gcmt-panel{position:fixed;top:0;right:0;height:100vh;width:360px;max-width:92vw;background:#fff;border-left:1px solid #b1b4b6;box-shadow:-2px 0 12px rgba(0,0,0,.15);z-index:2147483001;transform:translateX(100%);transition:transform .2s;display:flex;flex-direction:column}' +
      '.gcmt-panel.gcmt-open{transform:none}' +
      '.gcmt-head{display:flex;align-items:center;gap:8px;padding:14px 16px;border-bottom:1px solid #b1b4b6;background:#00267f;color:#fff}' +
      '.gcmt-head h2{margin:0;font-size:18px;flex:1}.gcmt-head button{background:none;border:0;color:#fff;font-size:22px;cursor:pointer;line-height:1}' +
      '.gcmt-head button:focus-visible{outline:3px solid #ffbf47;outline-offset:2px}' +
      '.gcmt-sub{display:flex;align-items:center;gap:6px;padding:8px 16px;font-size:14px;color:#505a5f;border-bottom:1px solid #e0e4e9}' +
      '.gcmt-list{flex:1;overflow:auto;padding:8px 0}' +
      '.gcmt-empty{padding:24px 16px;color:#505a5f;font-size:15px}' +
      '.gcmt-thread{padding:12px 16px;border-bottom:1px solid #e0e4e9}.gcmt-thread[data-resolved]{opacity:.6}' +
      '.gcmt-quote{font-size:13px;color:#505a5f;border-left:3px solid #ffc726;padding-left:8px;margin-bottom:6px}' +
      '.gcmt-msg{margin:6px 0}.gcmt-meta{font-size:12px;color:#505a5f}.gcmt-body{font-size:15px;margin:2px 0;white-space:pre-wrap;word-wrap:break-word}' +
      '.gcmt-actions{display:flex;gap:10px;margin-top:6px}' +
      '.gcmt-actions button{background:none;border:0;color:#1d70b8;font-size:13px;font-weight:700;cursor:pointer;padding:0}' +
      '.gcmt-actions button:focus-visible{outline:3px solid #ffbf47;outline-offset:2px}' +
      '.gcmt-reply{display:flex;gap:6px;margin-top:8px}.gcmt-reply textarea{flex:1;font:inherit;font-size:14px;border:1px solid #b1b4b6;border-radius:4px;padding:6px;resize:vertical;min-height:34px}' +
      '.gcmt-ft{padding:11px 16px;border-top:1px solid #e0e4e9;display:flex;flex-direction:column;gap:8px}' +
      '.gcmt-ft input{width:100%;box-sizing:border-box;font:inherit;font-size:14px;border:1px solid #b1b4b6;border-radius:4px;padding:7px 9px}' +
      '.gcmt-ft .gcmt-hintline{font-size:12px;color:#505a5f}' +
      '.gcmt-btn{background:#0e5f64;color:#fff;border:0;border-radius:4px;padding:7px 12px;font-size:14px;font-weight:700;cursor:pointer}.gcmt-btn:hover{background:#0a4549}' +
      '.gcmt-btn--ghost{background:#eef0f2;color:#0b0c0c}.gcmt-btn--ghost:hover{background:#dce0e4}' +
      '.gcmt-btn:focus-visible{outline:3px solid #ffbf47;outline-offset:2px}' +
      '.gcmt-selbtn{position:absolute;z-index:2147483002;background:#0e5f64;color:#fff;border:0;border-radius:18px;padding:6px 12px;font-size:14px;font-weight:700;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.3)}' +
      '.gcmt-composer{position:absolute;z-index:2147483003;background:#fff;border:1px solid #b1b4b6;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,.2);padding:10px;width:280px}' +
      '.gcmt-composer textarea{width:100%;font:inherit;font-size:14px;border:1px solid #b1b4b6;border-radius:4px;padding:6px;resize:vertical;min-height:60px;box-sizing:border-box}' +
      '.gcmt-composer .gcmt-row{display:flex;justify-content:flex-end;gap:8px;margin-top:8px}' +
      '.gcmt-composer .gcmt-cancel{background:none;border:0;color:#505a5f;font-weight:700;cursor:pointer}';
    document.head.appendChild(css);

    toggleBtn = el('button', 'gcmt-toggle');
    toggleBtn.type = 'button';
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.setAttribute('aria-label', 'Open the prototype review comments panel (developer tool)');
    toggleBtn.addEventListener('click', function () { panel.classList.contains('gcmt-open') ? closePanel() : openPanel(); });
    document.body.appendChild(toggleBtn);

    panel = el('aside', 'gcmt-panel');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Prototype review comments');

    var head = el('div', 'gcmt-head');
    head.appendChild(el('h2', '', 'Comments'));
    var close = el('button', ''); close.type = 'button'; close.textContent = '×'; close.setAttribute('aria-label', 'Close comments');
    close.addEventListener('click', closePanel);
    head.appendChild(close);

    var sub = el('div', 'gcmt-sub');
    resolvedChk = el('input'); resolvedChk.type = 'checkbox'; resolvedChk.id = 'gcmt-showres';
    resolvedChk.addEventListener('change', function () { showResolved = resolvedChk.checked; refresh(); });
    var lbl = el('label', '', 'Show resolved'); lbl.setAttribute('for', 'gcmt-showres');
    sub.appendChild(resolvedChk); sub.appendChild(lbl);

    listEl = el('div', 'gcmt-list');

    var ft = el('div', 'gcmt-ft');
    authorInput = el('input'); authorInput.type = 'text'; authorInput.placeholder = 'Your name (optional)';
    authorInput.setAttribute('aria-label', 'Your name'); authorInput.value = getAuthor();
    authorInput.addEventListener('change', function () { setItem(CFG.authorKey, authorInput.value.trim()); });
    hint = el('div', 'gcmt-hintline', 'Select any text on the page to add a comment.');
    var exportBtn = el('button', 'gcmt-btn gcmt-btn--ghost', 'Export all'); exportBtn.type = 'button';
    exportBtn.addEventListener('click', exportAll);
    ft.appendChild(authorInput); ft.appendChild(hint); ft.appendChild(exportBtn);

    panel.appendChild(head); panel.appendChild(sub); panel.appendChild(listEl); panel.appendChild(ft);
    document.body.appendChild(panel);

    document.addEventListener('mouseup', onSelect);
    document.addEventListener('keyup', onSelect);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (composer) { removeComposer(); return; }
        if (panel.classList.contains('gcmt-open')) { closePanel(); toggleBtn.focus(); }
      }
    });
  }

  function openPanel() { panel.classList.add('gcmt-open'); toggleBtn.setAttribute('aria-expanded', 'true'); renderPanel(); }
  function closePanel() { panel.classList.remove('gcmt-open'); toggleBtn.setAttribute('aria-expanded', 'false'); }

  function renderToggle() {
    var n = threads.filter(function (t) { return !t.resolved; }).length;
    toggleBtn.textContent = '💬 Comments' + (n ? ' (' + n + ')' : '');
  }

  function renderPanel() {
    if (!listEl) return;
    listEl.innerHTML = '';
    var visible = threads.filter(function (t) { return showResolved || !t.resolved; });
    if (!visible.length) {
      listEl.appendChild(el('div', 'gcmt-empty', 'No comments on this page yet. Select any text to start one.'));
      return;
    }
    visible.forEach(function (t) {
      var box = el('div', 'gcmt-thread'); box.dataset.thread = t.id; if (t.resolved) box.setAttribute('data-resolved', '1');
      box.appendChild(el('div', 'gcmt-quote', '“' + t.quote + '”'));
      box.appendChild(msg(t.author, t.text, t.createdAt));
      (t.replies || []).forEach(function (r) { box.appendChild(msg(r.author, r.text, r.createdAt)); });
      var actions = el('div', 'gcmt-actions');
      var reBtn = el('button', '', 'Reply'); reBtn.type = 'button'; reBtn.addEventListener('click', function () { showReply(box, t.id); });
      var resBtn = el('button', '', t.resolved ? 'Reopen' : 'Resolve'); resBtn.type = 'button';
      resBtn.addEventListener('click', function () { setResolved(t.id, !t.resolved); });
      actions.appendChild(reBtn); actions.appendChild(resBtn); box.appendChild(actions);
      box.addEventListener('click', function () { flash(t.id); });
      listEl.appendChild(box);
    });
  }
  function msg(author, text, ts) {
    var wrap = el('div', 'gcmt-msg');
    wrap.appendChild(el('div', 'gcmt-meta', (author || 'anonymous') + ' · ' + when(ts)));
    wrap.appendChild(el('div', 'gcmt-body', text));
    return wrap;
  }
  function showReply(box, id) {
    if (box.querySelector('.gcmt-reply')) return;
    var wrap = el('div', 'gcmt-reply'), ta = el('textarea'), send = el('button', 'gcmt-btn', 'Post');
    send.type = 'button';
    ta.setAttribute('aria-label', 'Write a reply');
    send.addEventListener('click', function () {
      var v = ta.value.trim(); if (!v) return;
      var list = load(pageKey()), t = list.find(function (x) { return x.id === id; });
      if (t) { (t.replies = t.replies || []).push({ id: uid(), author: getAuthor(), text: v, createdAt: Date.now() }); save(pageKey(), list); }
      refresh();
    });
    wrap.appendChild(ta); wrap.appendChild(send); box.appendChild(wrap); ta.focus();
  }
  function setResolved(id, resolved) {
    var list = load(pageKey()), t = list.find(function (x) { return x.id === id; });
    if (t) { t.resolved = resolved; save(pageKey(), list); }
    refresh();
  }
  function focusThread(id) {
    var box = listEl.querySelector('.gcmt-thread[data-thread="' + id + '"]');
    if (box) box.scrollIntoView({ block: 'center' });
    flash(id);
  }
  function flash(id) {
    var m = document.querySelector('mark.gcmt-hl[data-thread="' + id + '"]');
    if (m) { m.scrollIntoView({ block: 'center', behavior: 'smooth' }); m.classList.add('gcmt-flash'); setTimeout(function () { m.classList.remove('gcmt-flash'); }, 1200); }
  }

  /* ---- selection -> new comment ---- */
  function onSelect() {
    setTimeout(function () {
      removeSelBtn();
      var sel = window.getSelection();
      if (!sel || sel.isCollapsed) return;
      var range = sel.getRangeAt(0);
      if (!rootEl().contains(range.commonAncestorContainer)) return;
      if (range.startContainer.parentElement && range.startContainer.parentElement.closest('[data-gcmt]')) return;
      var quote = sel.toString().trim();
      if (quote.length < 2) return;
      var rect = range.getBoundingClientRect();
      var saved = { quote: quote, prefix: ctx(range, -32, 'start'), suffix: ctx(range, 32, 'end') };
      selBtn = el('button', 'gcmt-selbtn'); selBtn.type = 'button'; selBtn.textContent = '💬 Comment';
      selBtn.style.top = (window.scrollY + rect.bottom + 6) + 'px';
      selBtn.style.left = (window.scrollX + rect.left) + 'px';
      selBtn.addEventListener('mousedown', function (e) { e.preventDefault(); });
      selBtn.addEventListener('click', function (e) { e.stopPropagation(); openComposer(saved, rect); });
      document.body.appendChild(selBtn);
    }, 1);
  }
  function ctx(range, n, which) {
    try {
      var ix = buildIndex(rootEl());
      var node = which === 'start' ? range.startContainer : range.endContainer;
      var off = which === 'start' ? range.startOffset : range.endOffset;
      var seg = ix.map.find(function (s) { return s.node === node; });
      var g = seg ? seg.start + off : ix.full.indexOf(range.toString());
      if (g < 0) return '';
      return n < 0 ? ix.full.slice(Math.max(0, g + n), g) : ix.full.slice(g, g + n);
    } catch (e) { return ''; }
  }
  function removeSelBtn() { if (selBtn) { selBtn.remove(); selBtn = null; } }
  function removeComposer() { if (composer) { composer.remove(); composer = null; } }

  function openComposer(saved, rect) {
    removeSelBtn(); removeComposer();
    composer = el('div', 'gcmt-composer');
    composer.style.top = (window.scrollY + rect.bottom + 6) + 'px';
    composer.style.left = (window.scrollX + Math.min(rect.left, window.innerWidth - 300)) + 'px';
    var ta = el('textarea'); ta.placeholder = 'Add your comment…'; ta.setAttribute('aria-label', 'Add your comment');
    var row = el('div', 'gcmt-row');
    var cancel = el('button', 'gcmt-cancel', 'Cancel'); cancel.type = 'button'; cancel.addEventListener('click', removeComposer);
    var post = el('button', 'gcmt-btn', 'Comment'); post.type = 'button';
    post.addEventListener('click', function () {
      var v = ta.value.trim(); if (!v) return;
      var list = load(pageKey());
      list.push({ id: uid(), quote: saved.quote, prefix: saved.prefix, suffix: saved.suffix, author: getAuthor(), text: v, createdAt: Date.now(), resolved: false, replies: [] });
      save(pageKey(), list);
      removeComposer(); window.getSelection().removeAllRanges();
      refresh(); openPanel();
    });
    ta.addEventListener('keydown', function (e) { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); post.click(); } });
    row.appendChild(cancel); row.appendChild(post);
    composer.appendChild(ta); composer.appendChild(row);
    document.body.appendChild(composer); ta.focus();
  }
  document.addEventListener('mousedown', function (e) {
    if (composer && !composer.contains(e.target)) removeComposer();
    if (selBtn && e.target !== selBtn) removeSelBtn();
  });

  /* ---- go ---- */
  function init() {
    buildUI();
    refresh();
    // Re-scope when a single-page framework flow swaps its H1.
    var watch = document.getElementById('app') || document.body;
    var lastKey = pageKey();
    try {
      new MutationObserver(function () {
        var k = pageKey();
        if (k !== lastKey) { lastKey = k; refresh(); }
      }).observe(watch, { childList: true, subtree: true });
    } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();

/* ============================================================================
   GovBB prototype dev tools — Auto-fill (PROTOTYPE DEV TOOL)
   ----------------------------------------------------------------------------
   Drop-in, self-contained. Paste this whole block in a <script> tag AFTER the
   govbb-framework.js include and after the form's FLOW / PAGES / nav() are
   defined (i.e. at the very end of <body>).

   Adds TWO frosted-glass pills, bottom-right:
     ✎  Fill this page   — fills only the fields on the page you're looking at,
                           then re-renders so conditional fields appear.
     ⚡  Fill all → Check  — walks the whole flow, fills every page, and lands
                           on Check Your Answers (the original behaviour).

   Dev-only: this tool has its OWN gate, separate from comments. The pills
   appear only when the URL has ?dev or the hash contains "autofill"
   (#autofill). Nothing else enables it — not ?comment, not localhost, not
   file:// — so a dev link can turn auto-fill on without turning comments on.
   They never show for real users (no param).

   Works on ANY form built with the framework because it reads each field's
   data-field id + element type and infers a value — no per-form config.
   Only fills EMPTY fields, so it completes a partly-typed form without
   clobbering what you entered. On a page with no form fields (a directory, a
   content page) "Fill this page" simply does nothing and "Fill all" no-ops.

   Pairs with comments.js (bottom-LEFT), so the two tools never collide.
   ========================================================================== */
(function () {
  'use strict';

  /* ---- dev gate: auto-fill tool only, via ?dev / #autofill ---- */
  var showAutofill =
    /[?&]dev\b/.test(location.search) ||
    location.hash.indexOf('autofill') !== -1;
  if (!showAutofill) return;

  /* Resolve the flow-navigation function. Some prototypes expose a global
     nav(); others expose it as GovBB.nav(). Accept either so the tool works
     across framework variants without a per-form shim. */
  var navFn =
    (typeof nav === 'function') ? nav :
    (typeof GovBB !== 'undefined' && typeof GovBB.nav === 'function') ? GovBB.nav :
    null;

  var hasFramework =
    typeof GovBB !== 'undefined' && typeof FLOW !== 'undefined' && navFn !== null;

  /* ---- sample data ---- */
  var SAMPLE = {
    firstName: 'Ava',
    middleName: 'Marie',
    lastName: 'Belgrave',
    fullName: 'Ava Belgrave',
    email: 'ava.belgrave@example.com',
    nrn: '870315-1234',
    line1: '12 Bay Street',
    line2: 'Bridgetown',
    eventName: 'Oistins Summer Food Fair',
    orgName: 'Bridgetown Events Ltd',
    sentence: 'Fish from Oistins market; flour, oil and dry goods from a wholesaler.'
  };

  /* Build a plausible date from a field prefix (id minus the -day/-month/-year).
     from/start  -> ~3 weeks out (satisfies "apply at least 2 weeks ahead")
     to/end      -> ~3 weeks + 2 days out
     anything else (e.g. a date of birth) -> 30 years ago */
  function dateForPrefix(prefix) {
    var t = new Date();
    if (/from|start|begin/i.test(prefix)) t.setDate(t.getDate() + 21);
    else if (/to|end|until|expiry|expire/i.test(prefix)) t.setDate(t.getDate() + 23);
    else t.setFullYear(t.getFullYear() - 30);
    return { day: String(t.getDate()), month: String(t.getMonth() + 1), year: String(t.getFullYear()) };
  }

  /* Pick a real option from a <select> (skip the empty placeholder). */
  function pickOption(sel) {
    var opts = [].slice.call(sel.options).filter(function (o) { return o.value; });
    if (!opts.length) return '';
    // second real option when available — avoids always the alphabetically-first
    return (opts[1] || opts[0]).value;
  }

  /* Heuristic value for a text / textarea / date field. */
  function valueFor(id, el) {
    var lid = id.toLowerCase();
    var tag = el.tagName.toLowerCase();
    var type = (el.getAttribute('type') || '').toLowerCase();
    var im = (el.getAttribute('inputmode') || '').toLowerCase();

    // date parts: e.g. event-from-day / event-from-month / event-from-year
    var m = lid.match(/^(.*)-(day|month|year)$/);
    if (m) return dateForPrefix(m[1])[m[2]];

    if (tag === 'textarea') return SAMPLE.sentence;

    if (type === 'email' || lid.indexOf('email') !== -1) return SAMPLE.email;
    if (type === 'tel' || lid.indexOf('phone') !== -1 || /\btel\b/.test(lid)) return '(246) 424 1234';

    if (lid.indexOf('nrn') !== -1 || lid.indexOf('national') !== -1) return SAMPLE.nrn;

    if (lid.indexOf('first') !== -1) return SAMPLE.firstName;
    if (lid.indexOf('middle') !== -1) return SAMPLE.middleName;
    if (lid.indexOf('surname') !== -1 || lid.indexOf('last') !== -1) return SAMPLE.lastName;
    if (lid.indexOf('organiser') !== -1 || lid.indexOf('organizer') !== -1) return SAMPLE.orgName;
    if (lid.indexOf('event') !== -1 && lid.indexOf('name') !== -1) return SAMPLE.eventName;
    if (lid.indexOf('name') !== -1) return SAMPLE.fullName;
    if (lid.indexOf('line1') !== -1) return SAMPLE.line1;
    if (lid.indexOf('line2') !== -1) return SAMPLE.line2;

    // numeric fields (counts etc.)
    if (im === 'numeric' || /\bnum|number|count|patron|stall|quantity|amount\b/.test(lid)) {
      if (/patron/.test(lid)) return '150';
      if (/stall/.test(lid)) return '8';
      return '5';
    }

    return 'Sample ' + lid.replace(/[-_]/g, ' ');
  }

  /* Fill every field currently rendered in #app. Mutates GovBB.D. */
  function fillCurrentPage() {
    if (!hasFramework) return;
    var app = document.getElementById('app');
    if (!app) return;
    var expanders = 0, plainChecks = 0;

    [].forEach.call(app.querySelectorAll('[data-field]'), function (el) {
      var id = el.getAttribute('data-field');
      var tag = el.tagName.toLowerCase();
      var type = (el.getAttribute('type') || '').toLowerCase();

      if (tag === 'input' && type === 'radio') {
        if (!GovBB.D[id]) GovBB.D[id] = el.value;   // first option wins
        return;
      }
      if (tag === 'input' && type === 'checkbox') {
        var isExpander = el.hasAttribute('data-trigger-render');
        if (GovBB.D[id]) return;
        if (isExpander) { if (expanders < 2) { GovBB.D[id] = true; expanders++; } }
        else { if (plainChecks < 3) { GovBB.D[id] = true; plainChecks++; } }
        return;
      }
      if (tag === 'select') {
        if (!GovBB.D[id]) GovBB.D[id] = pickOption(el);
        return;
      }
      // text / textarea / date parts
      if (!GovBB.D[id]) GovBB.D[id] = valueFor(id, el);
    });

    // fake any file uploads on this page so Check shows a document attached
    [].forEach.call(app.querySelectorAll('input[type="file"][id^="upload-"]'), function (el) {
      var key = el.id.replace(/^upload-/, '');
      if (!GovBB.D['upload-' + key]) {
        GovBB.D['upload-' + key] = { name: 'sample-document.pdf', size: 245678, type: 'application/pdf' };
      }
    });
  }

  /* Re-render the page we're on so newly-filled values (and any conditionals
     they trigger) show. We don't know the current page id, so re-run the whole
     current view: the framework re-renders #app from GovBB.D on nav(). We find
     the current page by asking the framework, falling back to a soft refresh. */
  function currentPageId() {
    if (GovBB && GovBB.current) return GovBB.current;           // if the framework tracks it directly
    if (GovBB && typeof GovBB.getCurrentIndex === 'function') { // index-based frameworks (GovBB.getFlow/getCurrentIndex)
      var flow = typeof GovBB.getFlow === 'function' ? GovBB.getFlow() : (typeof FLOW !== 'undefined' ? FLOW : null);
      var i = GovBB.getCurrentIndex();
      if (flow && i != null && flow[i]) return flow[i];
    }
    if (location.hash) return location.hash.replace(/^#/, '');  // hash-routed flows
    return null;
  }

  /* "Fill this page": fill, then fill again after a re-render to catch the
     conditional fields the first pass revealed. */
  function fillThisPage() {
    if (!hasFramework) return;
    var pid = currentPageId();
    fillCurrentPage();
    if (pid && FLOW.indexOf(pid) !== -1) {
      navFn(pid);          // re-render — reveals data-trigger-render conditionals
      fillCurrentPage();   // fill the revealed fields
    }
  }

  /* "Fill all → Check": walk the flow, fill each page twice, land on Check. */
  function autofillAll() {
    if (!hasFramework) return;
    FLOW.forEach(function (pageId) {
      if (pageId === 'confirmation') return;
      navFn(pageId);        // render page
      fillCurrentPage();    // fill top-level fields
      navFn(pageId);        // re-render — reveals data-trigger-render conditionals
      fillCurrentPage();    // fill the revealed fields
    });
    navFn(FLOW.indexOf('check') !== -1 ? 'check' : FLOW[FLOW.length - 1]);
  }

  /* ---- shared frosted-glass styling (dev overlay only) ------------------
     These styles deliberately sit OUTSIDE the design system. They are a hidden
     developer overlay, never part of the shipped service, so the "use govbb-
     classes only / no custom CSS" rule does not apply here. ------------------ */
  if (!document.getElementById('govbb-devtool-glass')) {
    var css = document.createElement('style');
    css.id = 'govbb-devtool-glass';
    css.textContent = [
      '.govbb-dev{position:fixed;z-index:2147483000;font:600 14px/1 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}',
      '.govbb-dev__pill{display:inline-flex;align-items:center;gap:8px;padding:11px 18px;',
      '  border-radius:999px;cursor:pointer;color:#0b1c4b;',
      '  background:rgba(255,255,255,.55);',
      '  -webkit-backdrop-filter:blur(14px) saturate(1.6);backdrop-filter:blur(14px) saturate(1.6);',
      '  border:1px solid rgba(255,255,255,.65);',
      '  box-shadow:0 6px 24px rgba(11,28,75,.22),inset 0 1px 0 rgba(255,255,255,.7)}',
      '.govbb-dev__pill:hover{background:rgba(255,255,255,.72)}',
      '.govbb-dev__pill:focus-visible{outline:3px solid #ffbf47;outline-offset:2px}',
      '.govbb-dev__pill--go{color:#0b1c4b;background:rgba(120,150,255,.28);border-color:rgba(255,255,255,.6)}',
      '.govbb-dev__pill--go:hover{background:rgba(120,150,255,.42)}',
      '@media (prefers-color-scheme:dark){',
      '  .govbb-dev__pill{color:#eaf0ff;background:rgba(22,26,40,.5);border-color:rgba(255,255,255,.18);',
      '    box-shadow:0 6px 24px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.12)}',
      '  .govbb-dev__pill:hover{background:rgba(30,36,56,.62)}',
      '  .govbb-dev__pill--go{color:#eaf0ff;background:rgba(90,120,255,.34)}',
      '}'
    ].join('');
    document.head.appendChild(css);
  }

  /* ---- floating pills, bottom-right, stacked ---- */
  var wrap = document.createElement('div');
  wrap.className = 'govbb-dev';
  wrap.style.cssText = 'right:20px;bottom:20px;display:flex;flex-direction:column;gap:10px;align-items:flex-end';

  function pill(label, aria, mod, onClick) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'govbb-dev__pill' + (mod ? ' govbb-dev__pill--' + mod : '');
    b.textContent = label;
    b.setAttribute('aria-label', aria);
    b.addEventListener('click', onClick);
    return b;
  }

  if (hasFramework) {
    wrap.appendChild(pill('✎  Fill this page',
      'Fill the current page with sample data (developer tool)', '', fillThisPage));
    wrap.appendChild(pill('⚡  Fill all → Check',
      'Fill the whole form with sample data and go to Check Your Answers (developer tool)', 'go', autofillAll));
  }
  // If there's no framework, we render nothing — nothing to fill.
  if (wrap.childNodes.length) document.body.appendChild(wrap);
})();

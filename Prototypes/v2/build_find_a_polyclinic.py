#!/usr/bin/env python3
"""Build the Find a polyclinic prototype (v2) from polyclinics.json.

Run:  python3 build_find_a_polyclinic.py
Writes:
  find-a-polyclinic.html              entry page (light: what it is, start button, emergency, cost, help)
  find-a-polyclinic/find.html         Search for a polyclinic (filters + result cards)
  find-a-polyclinic/<slug>.html       one detail page per polyclinic / outpatient clinic

Copies the live alpha.gov.bb service find-an-open-pharmacy (entry -> /find -> /<slug>):
same page shapes, same classes, same card and detail layouts. Opening times and
everything specific to one site live on that site's detail page, not the entry page.
Edit the data, not the generated pages.
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'polyclinics.json'), encoding='utf-8'))
SITES = {s['slug']: s for s in DATA['sites']}
MIN = DATA['ministry']
PHARMACY = 'https://alpha.gov.bb/health-and-emergency-services/find-an-open-pharmacy/'
FREE_MEDS = 'https://alpha.gov.bb/health-and-emergency-services/free-or-subsidised-medication'
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
SHORT = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 0: 'Sun'}
e = html.escape


def digits(num):
    return ''.join(c for c in num if c.isdigit())


def tel(num):
    return f'<a class="govbb-link" style="white-space:nowrap" href="tel:+1{digits(num)}">{e(num)}</a>'


def fmt(t, spaced=False):
    h, m = map(int, t.split(':'))
    suffix = 'am' if h < 12 else 'pm'
    h12 = h % 12 or 12
    base = f'{h12}:{m:02d}' if m else f'{h12}'
    return f'{base} {suffix}' if spaced else f'{base}{suffix}'


def kind(s):
    return 'Outpatient clinic' if s.get('outpatient') else 'Polyclinic'


def maps_url(s):
    return 'https://www.google.com/maps/search/?api=1&query=' + e(f'{s["name"]}, {s["address"]}, Barbados').replace(' ', '%20')


def call_target(s):
    """(label, number) for the Call button. Sites without a published number fall back to
    the parent polyclinic, then the Ministry."""
    parent = SITES.get(s.get('parent', ''))
    if s.get('phone'):
        return f'Call {s["phone"]}', s['phone']
    if parent and parent.get('phone'):
        return f'Call {parent["name"]}', parent['phone']
    return 'Call the Ministry', MIN['phone']


def hours_summary(s):
    """One line for result cards, like the live 'Mon–Fri 8:30am–4:30pm'."""
    hrs = s.get('hours')
    if hrs is None:
        return 'Clinic hours not confirmed'
    if hrs.get('allDay'):
        return 'Open 24 hours, every day'
    d = sorted(hrs['days'])
    days = f'{SHORT[d[0]]}–{SHORT[d[-1]]}' if d == list(range(d[0], d[-1] + 1)) and len(d) > 2 else ', '.join(SHORT[x] for x in d)
    return f'{days} {fmt(hrs["open"])}–{fmt(hrs["close"])}'


# --------------------------------------------------------------------------- shared chrome

def head(title, desc, css, extra_head='', dev_notes=''):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}" />
<link rel="icon" href="https://alpha.gov.bb/favicon.ico" />
<link rel="stylesheet" href="{css}" />
{extra_head}{dev_notes}
<style>
  :root{{--govbb-color-focus:#0a6c73}}
  /* No mobile heading override: the live build scales headings itself. */
  .pc-section{{display:flex;flex-direction:column;gap:var(--govbb-space-s)}}
  .pc-section > :where(p,ul,ol,dl){{max-inline-size:var(--govbb-measure);margin:0}}
  .pc-dot{{display:inline-block;width:.5rem;height:.5rem;border-radius:50%;margin-right:.5rem;vertical-align:middle;background:var(--govbb-grey-70,#595959)}}
  .pc-dot--open{{background:#00703c}} .pc-dot--soon{{background:#b35c00}} .pc-dot--closed{{background:#b10e1e}}
  .pc-st--open{{color:#00703c}} .pc-st--soon{{color:#8a4600}} .pc-st--closed{{color:#b10e1e}} .pc-st--unknown{{color:#3d3d3d}}
  .pc-muted{{color:var(--govbb-color-muted,#595959)}}
  .pc-today{{background:var(--govbb-blue-10,#e5e9f2);font-weight:700}}
  .pc-cols{{columns:2;column-gap:var(--govbb-space-l,2rem)}} .pc-cols li{{break-inside:avoid}}
  @media (max-width:40rem){{.pc-cols{{columns:1}}}}
  .pc-meta{{display:grid;grid-template-columns:11rem 1fr;gap:4px var(--govbb-space-s)}}
  .pc-meta dt{{font-weight:700}} .pc-meta dd{{margin:0;min-width:0;overflow-wrap:anywhere}}
  @media (max-width:30rem){{.pc-meta{{grid-template-columns:1fr}} .pc-meta dd{{margin-bottom:var(--govbb-space-xs)}}}}
  .pc-map{{display:block;width:100%;max-inline-size:var(--govbb-measure);height:240px;border:1px solid var(--govbb-grey-20);border-radius:var(--govbb-radius)}}
  .pc-emergency{{border:2px solid var(--govbb-color-error,#b10e1e);border-radius:var(--govbb-radius);padding:var(--govbb-space-s);max-inline-size:var(--govbb-measure)}}
  .pc-emergency > *{{margin:0}} .pc-emergency > * + *{{margin-top:var(--govbb-space-xs)}}
  .placeholder{{background:#fff2d6;border:2px dashed #d9a441;padding:1px 6px;font-size:.85em}}
</style>
</head>
<body class="govbb-page">
<a class="govbb-skip-link" href="#main-content">Skip to main content</a>

<div class="govbb-official-banner">
  <div class="govbb-official-banner__inner govbb-width-container">
    <span class="govbb-official-banner__crest"><img class="govbb-official-banner__icon" src="https://alpha.gov.bb/images/coat-of-arms.png" alt="" width="20" height="20" /></span>
    <span class="govbb-official-banner__text">An official website of the Government of Barbados</span>
  </div>
</div>

<header class="govbb-header" data-govbb-header-enhanced="true">
  <div class="govbb-width-container govbb-header__inner">
    <a href="#" class="govbb-header__home"><img class="govbb-header__logo" src="https://alpha.gov.bb/assets/govbb-logo-dweJzbng.svg" alt="Go to the alpha.gov.bb homepage" /></a>
    <div class="govbb-header__controls">
      <button type="button" class="govbb-button govbb-button--ghost govbb-header__toggle" aria-expanded="false" aria-controls="site-nav">Menu</button>
    </div>
    <nav id="site-nav" class="govbb-header__nav" aria-label="Primary navigation" data-expanded="false">
      <div class="govbb-header__nav-inner">
        <a href="#" class="govbb-link">Services</a>
        <a class="govbb-link" href="#">Track my application</a>
        <a class="govbb-button" href="#">Ask Assistant</a>
      </div>
    </nav>
  </div>
</header>

<div class="govbb-status-banner govbb-status-banner--alpha govbb-status-banner--full-width">
  <div class="govbb-status-banner__inner govbb-width-container">
    <p><span class="govbb-text-bold">Alpha</span> — this is a prototype. Opening hours and services are not confirmed by the Ministry of Health and Wellness.</p>
  </div>
</div>
'''


def breadcrumbs(items):
    lis = ''.join(f'<li class="govbb-breadcrumbs__item"><a class="govbb-link govbb-breadcrumbs__link" href="{h}">{e(t)}</a></li>' for t, h in items)
    return f'''
<div class="govbb-width-container">
  <nav class="govbb-breadcrumbs" aria-label="Breadcrumb">
    <ol class="govbb-breadcrumbs__list">{lis}</ol>
  </nav>
</div>
'''


FEEDBACK = '''<div class="govbb-width-container print:hidden">
    <aside class="govbb-feedback mb-4 lg:mb-16">
      <h3 class="govbb-feedback__heading">Was this helpful?</h3>
      <p class="govbb-text-body">Give us your feedback about this page.</p>
      <a class="govbb-link" href="#">Help us improve alpha.gov.bb</a>
    </aside>
  </div>'''

FOOT = '''
<footer class="govbb-footer">
  <div class="govbb-footer__inner govbb-width-container">
    <nav class="govbb-footer__nav" aria-label="Footer navigation">
      <ul class="govbb-footer__list">
        <li class="govbb-footer__item"><a class="govbb-footer__link" href="#">Home</a></li>
        <li class="govbb-footer__item"><a class="govbb-footer__link" href="#">Terms and conditions</a></li>
      </ul>
    </nav>
    <hr class="govbb-footer__divider" />
    <div class="govbb-footer__end">
      <img class="govbb-footer__coat" src="https://alpha.gov.bb/images/coat-of-arms.png" alt="" width="36" height="36" />
      <p class="govbb-footer__copy">&copy; 2026 Government of Barbados</p>
    </div>
  </div>
</footer>
<script>
/* Header menu toggle (the live header hides the nav behind "Menu" on small screens). */
(function(){var b=document.querySelector('.govbb-header__toggle'),n=document.getElementById('site-nav');
  if(!b||!n)return;b.addEventListener('click',function(){var o=b.getAttribute('aria-expanded')==='true';
  b.setAttribute('aria-expanded',String(!o));n.setAttribute('data-expanded',String(!o));});})();
</script>
'''

# Open/closed status in Barbados time (UTC-4, no daylight saving). Shared by search and detail pages.
STATUS_JS = r'''
var PC = (function(){
  function bbNow(){var n=new Date(new Date().toLocaleString('en-US',{timeZone:'America/Barbados'}));return {dow:n.getDay(),mins:n.getHours()*60+n.getMinutes()};}
  function hm(t){var p=t.split(':');return (+p[0])*60+(+p[1]);}
  function fmt(m){var hh=Math.floor(m/60),mm=m%60,s=hh<12?'am':'pm',h12=hh%12||12;return h12+(mm?':'+(mm<10?'0':'')+mm:'')+' '+s;}
  var names=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  /* returns {state:'open'|'soon'|'closed'|'unknown', lead:'Open', rest:'until 4:30 pm'} */
  function status(h){
    if(!h) return {state:'unknown',lead:'Hours not confirmed',rest:'Call before you go'};
    if(h.allDay) return {state:'open',lead:'Open',rest:'24 hours'};
    var t=bbNow(),o=hm(h.open),c=hm(h.close),today=h.days.indexOf(t.dow)!==-1;
    if(today&&t.mins>=o&&t.mins<c){var left=c-t.mins;
      return left<=60?{state:'soon',lead:'Closes soon',rest:'in '+left+' min at '+fmt(c)}:{state:'open',lead:'Open',rest:'until '+fmt(c)};}
    if(today&&t.mins<o) return {state:'closed',lead:'Closed',rest:'opens today at '+fmt(o)};
    for(var i=1;i<=7;i++){var d=(t.dow+i)%7;if(h.days.indexOf(d)!==-1)return {state:'closed',lead:'Closed',rest:'opens '+(i===1?'tomorrow':names[d])+' at '+fmt(o)};}
    return {state:'closed',lead:'Closed',rest:''};
  }
  function isOpen(h){var s=status(h).state;return s==='open'||s==='soon';}
  /* fill <p class="pc-status" data-hours="..."> */
  function paint(el,h){var s=status(h);el.className=el.className.replace(/\bpc-st--\w+/g,'')+' pc-st--'+s.state;
    el.innerHTML='<span aria-hidden="true" class="pc-dot pc-dot--'+s.state+'"></span>'+s.lead+(s.rest?' <span class="govbb-text-body-sm pc-muted" style="font-weight:400">'+s.rest+'</span>':'');}
  return {status:status,isOpen:isOpen,paint:paint,bbNow:bbNow};
})();
'''


# --------------------------------------------------------------------------- entry page

def entry_page():


    body = f'''{breadcrumbs([("Home", "#"), ("Health and emergency services", "#")])}
<main id="main-content" tabindex="-1">
  <div class="govbb-width-container govbb-main-wrapper">
    <div class="mb-xm lg:grid lg:grid-cols-3 lg:gap-16">
      <div class="space-y-6 lg:col-span-2 lg:space-y-8">
        <div class="space-y-4 lg:space-y-6">
          <h1 class="govbb-text-h1 wrap-anywhere">Find a polyclinic</h1>
          <div class="flex flex-col gap-xs"><div class="border-blue-10 border-b-4 pb-4 text-grey-70"><p class="govbb-text-body-sm">Last updated on {e(DATA["updated"])}</p></div></div>
        </div>
        <div class="govbb-prose">
          <p>Each area in Barbados has a polyclinic that offers health care to the people who live there. This is called a catchment area. Find out which polyclinic looks after your area, when it is open, and what services it offers.</p>
          <h2 id="in-an-emergency">In an emergency</h2>
          <p>For emergencies, go to the Queen Elizabeth Hospital’s Accident and Emergency Department, which is open 24 hours a day.</p>

          <h2 id="who-can-use-a-polyclinic">Who can use a polyclinic</h2>
          <p>If you are a Barbadian citizen who needs free health care, there are nine polyclinics across the island. Find the closest one to you and check its opening hours and services online before you go.</p>
          <p>While opening hours vary by location, Sir Winston Scott Polyclinic is open 24 hours a day, every day. Call ahead to confirm that the service you need is available.</p>
          <p><a class="govbb-button" href="find-a-polyclinic/find.html">Find a polyclinic</a></p>

          <h2 id="cost">Cost</h2>
          <p>Health care at a polyclinic is free. Polyclinic pharmacies provide prescription medication covered by the Barbados Drug Service free of charge.</p>

          <h2 id="get-help">Get help</h2>
          <p>Find out which polyclinic is for your area by entering your address or contacting the Ministry of Health and Wellness on {tel(MIN["phone"])} or <a class="govbb-link" href="mailto:{e(MIN["email"])}">{e(MIN["email"])}</a>.</p>
        </div>
      </div>
    </div>
  </div>
  {FEEDBACK}
</main>
{FOOT}
</body>
</html>
'''
    return head('Find a polyclinic | Government of Barbados',
                'Find a polyclinic or outpatient clinic in Barbados, check when it is open and what services it offers.',
                'govbb-alpha-styles.css') + body


# --------------------------------------------------------------------------- search page

FIND_DEV_NOTES = """<!-- DEV NOTES (generated by build_find_a_polyclinic.py — edit the data, not this file)
     Search by name or place: clinic names first, then addresses from Photon
     (photon.komoot.io, OpenStreetMap; no key, CORS-open), with a 36-village built-in
     Built-in place list first (instant): 644 places in polyclinics.json "places" from the
     GeoNames BB dump (CC-BY 4.0, geonames.org: needs attribution on a live page) plus
     version one's 36 villages. Photon results are merged in when they arrive (~1-4 s).
     Choosing a place sorts nearest first (straight line) and says whether it is in the
     Eunice Gibson catchment. Only that boundary is loaded: service introduced in phases.
     *** The catchment dataset has only been validated for ENVIRONMENTAL HEALTH routing.
     Using it to tell people their polyclinic is the assumption this prototype tests,
     not confirmed Ministry policy. Street-level geocoding is only a risk within ~150 m
     of the edge, so those addresses are told to call. ***
     OUTSIDE SERVICES: photon.komoot.io receives what the user types into the search box
     (place names, possibly a home address) and their IP address. Nothing is stored.
-->"""

def card(s):
    label, num = call_target(s)
    hrs = json.dumps(s.get('hours'))
    return f'''<li class="pc-card flex-col gap-3 rounded-lg border border-grey-20 bg-white-00 p-5 flex" data-slug="{s["slug"]}" data-parish="{e(s["parish"])}" data-kind="{"outpatient" if s.get("outpatient") else "polyclinic"}" data-lat="{s["lat"]}" data-lng="{s["lng"]}" data-hours="{e(hrs, quote=True)}" data-search="{e((s["name"] + " " + s["address"] + " " + s["parish"]).lower(), quote=True)}">
            <div class="min-h-5"><p class="pc-status govbb-text-body-sm govbb-text-bold"></p></div>
            <h3 class="govbb-text-h4"><a class="govbb-link" href="{s["slug"]}.html">{e(s["name"])}</a></h3>
            <p class="govbb-text-body-sm govbb-text-bold inline-flex w-fit items-center rounded-md px-3 py-1 bg-green-10 text-green-80">{kind(s)}: free health care</p>
            <div class="flex flex-col gap-1 text-grey-70">
              <p class="govbb-text-body-sm">{e(s["address"])}<span class="pc-distance"></span></p>
              <p class="govbb-text-body-sm"><span class="tabular-nums">{e(hours_summary(s))}</span></p>
            </div>
            <div class="flex flex-col gap-xs">
              <div class="flex flex-wrap items-center gap-2 print:hidden">
                <a class="govbb-button" href="tel:+1{digits(num)}">{e(label)}</a>
                <a class="govbb-button govbb-button--secondary" target="_blank" rel="noopener noreferrer" href="{maps_url(s)}">Directions<span class="govbb-visually-hidden"> to {e(s["name"])} (opens in a new tab)</span></a>
                <a class="govbb-button govbb-button--tertiary" href="{s["slug"]}.html">Full details<span class="govbb-visually-hidden"> for {e(s["name"])}</span></a>
              </div>
              <p class="govbb-text-body-sm hidden print:block">{e(label)}</p>
            </div>
          </li>'''


def find_page():
    sites = sorted(DATA['sites'], key=lambda s: (bool(s.get('outpatient')), s['name']))
    parishes = sorted({s['parish'] for s in sites})
    total = len(sites)
    parish_boxes = ''.join(
        f'<div class="govbb-checkbox-item"><input class="govbb-checkbox" id="parish-{i}" type="checkbox" value="{e(p)}" name="parish"><label class="govbb-checkbox-item__label" for="parish-{i}">{e(p)}</label></div>'
        for i, p in enumerate(parishes))
    cards = '\n          '.join(card(s) for s in sites)

    def group(gid, title, inner, open_=True):
        return f'''<div class="flex w-full flex-col gap-s border-grey-70 border-b pb-s">
                <h3 class="govbb-text-h4"><button aria-expanded="{str(open_).lower()}" aria-controls="{gid}" class="pc-group-toggle flex w-full items-center justify-between gap-2.5 text-left" type="button"><span>{title}</span><span class="text-teal-80" aria-hidden="true">{"−" if open_ else "+"}</span></button></h3>
                <div class="flex flex-col gap-s" id="{gid}"{"" if open_ else ' hidden style="display:none"'}>{inner}</div>
              </div>'''

    type_inner = '''<div class="govbb-form-group">
                  <label class="govbb-label" for="kind">Type of clinic</label>
                  <span class="govbb-hint" id="kind-hint">Outpatient clinics are smaller and offer fewer services. Each one is linked to a polyclinic.</span>
                  <select id="kind" class="govbb-select" aria-describedby="kind-hint"><option value="all">All types</option><option value="polyclinic">Polyclinic</option><option value="outpatient">Outpatient clinic</option></select>
                </div>'''
    hours_inner = '''<div class="govbb-checkbox-item">
                  <input class="govbb-checkbox" id="open-now" aria-describedby="open-now-hint" type="checkbox">
                  <label class="govbb-checkbox-item__label" for="open-now">Open right now</label>
                  <span class="govbb-hint" id="open-now-hint">Uses Barbados time and listed clinic hours. Clinics with hours not confirmed are left out. Call before travelling.</span>
                </div>'''

    ring = DATA['catchments']['eunice-gibson']['ring']
    ring_js, places_js = json.dumps(ring, separators=(',', ':')), json.dumps(DATA['places'], separators=(',', ':'), ensure_ascii=False)
    min_phone, min_tel, min_email = json.dumps(MIN['phone']), json.dumps('+1' + digits(MIN['phone'])), json.dumps(MIN['email'])

    filters = f'''<div class="mb-m flex flex-col gap-m lg:mb-0 print:hidden">
            <h2 class="govbb-text-h2 govbb-visually-hidden">Filter polyclinics</h2>
            <div>
              <button id="filter-toggle" aria-controls="filter-panel" aria-expanded="true" class="flex w-full items-center gap-xs border-grey-70 border-b py-3 text-green-80" type="button"><span class="govbb-text-body govbb-text-bold underline">Filter</span></button>
              <div class="flex flex-col gap-xm border-grey-20 border-b bg-grey-20 p-xm" id="filter-panel">
                <div class="flex flex-col gap-xs">
                  <button type="button" id="use-location" class="govbb-button self-start" aria-pressed="false">Use my location</button>
                  <p id="location-msg" class="govbb-text-body-sm" role="status"></p>
                </div>
                <div class="govbb-form-group pc-combo-group">
                  <label class="govbb-label" for="q">Search by name or place</label>
                  <span class="govbb-hint" id="q-hint">For example: Redmans, Highway 2A, or Rock Hall.</span>
                  <div class="govbb-combobox pc-combo">
                    <input id="q" class="govbb-input" type="text" role="combobox" aria-expanded="false" aria-controls="q-list" aria-autocomplete="list" aria-describedby="q-hint" autocomplete="off" spellcheck="false" value="">
                    <ul class="govbb-combobox__list pc-listbox" id="q-list" hidden role="listbox" aria-label="Polyclinics and places"></ul>
                  </div>
                  <p class="govbb-text-body-sm pc-muted" id="q-status" role="status" aria-live="polite"></p>
                </div>
                {group("grp-type", "Type", type_inner)}
                {group("grp-hours", "Opening hours", hours_inner)}
                {group("grp-parish", "Parish", parish_boxes, open_=False)}
              </div>
              <p class="govbb-text-body-sm text-grey-70" id="filter-summary" role="status"></p>
            </div>
          </div>'''

    body = rf'''{breadcrumbs([("Home", "#"), ("Health and emergency services", "#"), ("Find a polyclinic", "../find-a-polyclinic.html")])}
<main id="main-content" tabindex="-1">
  <div class="govbb-width-container govbb-main-wrapper">
    <div class="mb-l flex flex-col gap-m">
      <div class="flex flex-col gap-xs">
        <h1 class="govbb-text-h1">Search for a polyclinic</h1>
        <div class="border-blue-10 border-b-4 pb-4"><p class="govbb-text-body-sm">Last updated on {e(DATA["updated"])}.</p></div>
      </div>
      <p class="govbb-text-body">Find polyclinics and outpatient clinics across Barbados. Health care is free. Polyclinics appear first. In an emergency, go to the Queen Elizabeth Hospital’s Accident and Emergency Department.</p>
      <section aria-label="Polyclinic finder">
        <div class="govbb-grid-row">
          <div class="govbb-grid-column-one-third-from-desktop">
          {filters}
          </div>
          <div class="govbb-grid-column-two-thirds-from-desktop">
            <h2 class="govbb-text-h2 govbb-visually-hidden">Results</h2>
            <noscript><p class="govbb-text-body">Call the clinic before you go to confirm opening times.</p></noscript>
            <div id="area-answer" class="mb-s" role="status" aria-live="polite"></div>
            <p class="govbb-text-body govbb-text-bold mb-s" id="result-count" role="status" aria-atomic="true">Showing all {total} polyclinics and clinics</p>
            <ul class="flex list-none flex-col gap-s p-0" id="results">
          {cards}
            </ul>
            <div id="no-results" class="border-l-4 px-s py-xs border-yellow-80 bg-yellow-20" hidden>
              <p class="govbb-text-body">No polyclinics match your filters. <button type="button" class="govbb-link pc-clear" style="background:none;border:0;padding:0;cursor:pointer;font:inherit;text-decoration:underline">Clear all filters</button></p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
  {FEEDBACK}
</main>
{FOOT}
<script>
{STATUS_JS}
(function(){{
  var TOTAL={total};
  var list=document.getElementById('results'), cards=[].slice.call(list.querySelectorAll('.pc-card'));
  var q=document.getElementById('q'), kind=document.getElementById('kind'), openNow=document.getElementById('open-now');
  var parishBoxes=[].slice.call(document.querySelectorAll('input[name="parish"]'));
  var countEl=document.getElementById('result-count'), summary=document.getElementById('filter-summary'), none=document.getElementById('no-results');
  var here=null, hereLabel='', baseOrder=cards.slice();
  var RING={ring_js}, PLACES={places_js}, EG_SLUG='eunice-gibson-polyclinic', MIN_PHONE={min_phone}, MIN_TEL={min_tel}, MIN_EMAIL={min_email};
  var qList=document.getElementById('q-list'), qStatus=document.getElementById('q-status'), answer=document.getElementById('area-answer');

  /* Filter panel: open on desktop, collapsed on phones (as on the live pharmacy finder). */
  var toggle=document.getElementById('filter-toggle'), panel=document.getElementById('filter-panel');
  function setPanel(open){{toggle.setAttribute('aria-expanded',String(open));panel.hidden=!open;panel.style.display=open?'':'none';}}
  setPanel(window.matchMedia('(min-width: 64rem)').matches);
  toggle.addEventListener('click',function(){{setPanel(toggle.getAttribute('aria-expanded')!=='true');}});
  [].forEach.call(document.querySelectorAll('.pc-group-toggle'),function(b){{
    b.addEventListener('click',function(){{var o=b.getAttribute('aria-expanded')==='true',g=document.getElementById(b.getAttribute('aria-controls'));
      b.setAttribute('aria-expanded',String(!o));g.hidden=o;g.style.display=o?'none':'';b.lastElementChild.textContent=o?'+':'−';}});
  }});

  function km(a,b){{var R=6371,r=Math.PI/180,dLa=(b[0]-a[0])*r,dLo=(b[1]-a[1])*r;
    var x=Math.sin(dLa/2)*Math.sin(dLa/2)+Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin(dLo/2)*Math.sin(dLo/2);return 2*R*Math.asin(Math.sqrt(x));}}

  function apply(){{
    var term=(here&&q.value===hereLabel)?'':norm(q.value);
    if(term&&!cards.some(function(c){{return norm(c.dataset.search).indexOf(term)!==-1;}}))term='';
    var k=kind.value, on=openNow.checked;
    var ps=parishBoxes.filter(function(b){{return b.checked;}}).map(function(b){{return b.value;}});
    var shown=0;
    cards.forEach(function(c){{
      var ok=(!term||norm(c.dataset.search).indexOf(term)!==-1)
        &&(k==='all'||c.dataset.kind===k)
        &&(!ps.length||ps.indexOf(c.dataset.parish)!==-1)
        &&(!on||PC.isOpen(JSON.parse(c.dataset.hours)));
      c.hidden=!ok; c.style.display=ok?'':'none'; if(ok)shown++;
    }});
    countEl.textContent=shown===TOTAL?'Showing all '+TOTAL+' polyclinics and clinics':'Showing '+shown+' of '+TOTAL+' polyclinics and clinics';
    none.hidden=shown!==0;
    var n=(term?1:0)+(here?1:0)+(k!=='all'?1:0)+(on?1:0)+ps.length;
    summary.innerHTML=n?n+(n===1?' filter':' filters')+' applied. <button type="button" class="govbb-link pc-clear" style="background:none;border:0;padding:0;cursor:pointer;font:inherit;text-decoration:underline">Clear all filters</button>':'';
  }}

  function clearAll(){{clearOrigin();q.value='';closeList();qStatus.textContent='';kind.value='all';openNow.checked=false;parishBoxes.forEach(function(b){{b.checked=false;}});apply();q.focus();}}
  document.addEventListener('click',function(ev){{if(ev.target.classList&&ev.target.classList.contains('pc-clear'))clearAll();}});
  [kind,openNow].concat(parishBoxes).forEach(function(el){{el.addEventListener('change',apply);}});

  function norm(t){{return String(t).toLowerCase().replace(/[.,'’]/g,'').replace(/\bsaint\b/g,'st').replace(/\s+/g,' ').trim();}}
  function esc(t){{return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}

  /* ---- Which catchment? Only the Eunice Gibson boundary is loaded (service introduced in phases). */
  function inRing(lng,lat){{var inside=false;for(var i=0,j=RING.length-1;i<RING.length;j=i++){{
    var xi=RING[i][0],yi=RING[i][1],xj=RING[j][0],yj=RING[j][1];
    if(((yi>lat)!==(yj>lat))&&(lng<(xj-xi)*(lat-yi)/(yj-yi)+xi))inside=!inside;}}return inside;}}
  function edgeMetres(lng,lat){{var kx=111320*Math.cos(lat*Math.PI/180),ky=110540,best=Infinity;
    for(var i=0,j=RING.length-1;i<RING.length;j=i++){{
      var ax=(RING[j][0]-lng)*kx,ay=(RING[j][1]-lat)*ky,bx=(RING[i][0]-lng)*kx,by=(RING[i][1]-lat)*ky,dx=bx-ax,dy=by-ay,L2=dx*dx+dy*dy;
      var t=L2?Math.max(0,Math.min(1,-(ax*dx+ay*dy)/L2)):0,px=ax+t*dx,py=ay+t*dy,d=Math.sqrt(px*px+py*py);if(d<best)best=d;}}return best;}}
  var PHASED='<p class="govbb-text-body-sm">This service is being introduced in phases. It currently covers the area served by Eunice Gibson Polyclinic at Warrens and St. Thomas Outpatient Clinic at Rock Hall, which operates as part of the polyclinic.</p>';
  var OTHER='<p class="govbb-text-body-sm">For information about other areas, contact the Ministry of Health and Wellness at <a class="govbb-link" style="white-space:nowrap" href="tel:'+MIN_TEL+'">'+MIN_PHONE+'</a> or email <a class="govbb-link" href="mailto:'+MIN_EMAIL+'">'+MIN_EMAIL+'</a>.</p>';
  function showAnswer(lat,lng,label){{
    var inside=inRing(lng,lat), near=edgeMetres(lng,lat)<150;
    if(inside){{
      answer.innerHTML='<div class="border-l-4 px-s py-xs border-green-80 bg-green-10"><p class="govbb-text-body"><strong>'+esc(label)+'</strong> is in the area served by <a class="govbb-link" href="'+EG_SLUG+'.html">Eunice Gibson Polyclinic</a>.</p>'
        +(near?'<p class="govbb-text-body-sm">This is close to the edge of the area. Call Eunice Gibson Polyclinic to check before you go.</p>':'')
        +PHASED+'</div>';
    }} else {{
      answer.innerHTML='<div class="border-l-4 px-s py-xs border-yellow-80 bg-yellow-20"><p class="govbb-text-body">We cannot tell you which polyclinic is for <strong>'+esc(label)+'</strong> yet. The nearest are shown first.</p>'
        +(near?'<p class="govbb-text-body-sm">This is close to the edge of the Eunice Gibson Polyclinic area. Call Eunice Gibson Polyclinic to check.</p>':'')
        +PHASED+OTHER+'</div>';
    }}
  }}

  /* ---- Sort nearest first from a chosen place or the user's location. */
  function setOrigin(lat,lng,label,isAddress){{
    here=[lat,lng];hereLabel=isAddress?q.value:'';
    cards.forEach(function(c){{c._d=km(here,[+c.dataset.lat,+c.dataset.lng]);c.querySelector('.pc-distance').textContent=' · '+c._d.toFixed(1)+' km away';}});
    cards.slice().sort(function(a,b){{return a._d-b._d;}}).forEach(function(c){{list.appendChild(c);}});
    showAnswer(lat,lng,label);apply();
  }}
  function clearOrigin(){{
    if(!here)return;here=null;hereLabel='';answer.innerHTML='';
    locBtn.setAttribute('aria-pressed','false');locBtn.textContent='Use my location';locMsg.textContent='';
    baseOrder.forEach(function(c){{list.appendChild(c);c.querySelector('.pc-distance').textContent='';}});
  }}

  /* ---- Search by name or place: clinic names first, then Photon (OpenStreetMap) addresses,
     with a built-in village list if Photon is down. Same lookup as version one. */
  var opts=[],active=-1,timer=null,controller=null,lastQuery='';
  function clinicMatches(t){{var n=norm(t);if(n.length<2)return [];
    return cards.filter(function(c){{return norm(c.querySelector('h3').textContent).indexOf(n)!==-1;}}).slice(0,3)
      .map(function(c){{return {{type:'clinic',name:c.querySelector('h3').textContent,where:c.dataset.kind==='outpatient'?'Outpatient clinic':'Polyclinic',slug:c.dataset.slug}};}});}}
  /* Built-in place list (GeoNames + version one villages): answers instantly, before Photon replies. */
  function local(t){{var n=norm(t);if(n.length<2)return [];
    return PLACES.map(function(p){{var m=norm(p.n),i=m.indexOf(n);return {{p:p,r:i===0?0:(i>0&&m.charAt(i-1)===' ')?1:i>0?2:-1}};}})
      .filter(function(x){{return x.r>=0;}}).sort(function(a,b){{return a.r-b.r||a.p.n.localeCompare(b.p.n);}}).slice(0,6)
      .map(function(x){{return {{type:'place',name:x.p.n,where:x.p.p,lng:x.p.c[0],lat:x.p.c[1],local:1}};}});}}
  /* Same name in the same parish, or within ~650 m: the Photon copy adds nothing. */
  function samePlace(a,b){{return norm(a.name)===norm(b.name)&&((Math.abs(a.lat-b.lat)<0.006&&Math.abs(a.lng-b.lng)<0.006)||norm(b.where).slice(-norm(a.where).length)===norm(a.where));}}
  function photon(t){{
    if(controller)controller.abort();controller=window.AbortController?new AbortController():null;
    var url='https://photon.komoot.io/api/?q='+encodeURIComponent(t)+'&limit=8&lat=13.17&lon=-59.60&bbox=-59.70,13.03,-59.40,13.34';
    return fetch(url,controller?{{signal:controller.signal}}:undefined).then(function(r){{if(!r.ok)throw new Error('status');return r.json();}})
      .then(function(d){{return (d.features||[]).filter(function(f){{return f.properties&&f.properties.countrycode==='BB';}}).map(function(f){{
        var p=f.properties,c=f.geometry.coordinates;
        /* Parish matters: Barbados has two Rock Halls and two Welcheses. */
        var where=[p.street,p.district,p.city,p.county||p.state].filter(Boolean).filter(function(v,i,a){{return a.indexOf(v)===i;}}).join(', ').replace(/\bSaint\b/g,'St.');
        return {{type:'place',name:p.name||p.street||t,where:where,lng:c[0],lat:c[1]}};}}).filter(function(o){{return o.name&&!/polyclinic|outpatient clinic/i.test(o.name);}}).slice(0,7);}});
  }}
  function render(){{
    if(!opts.length){{qList.hidden=true;qList.innerHTML='';q.setAttribute('aria-expanded','false');q.removeAttribute('aria-activedescendant');return;}}
    qList.innerHTML=opts.map(function(o,i){{return '<li class="govbb-combobox__option pc-opt" id="q-opt-'+i+'" role="option" data-i="'+i+'" aria-selected="'+(i===active)+'"><span class="pc-opt__name">'+esc(o.name)+'</span>'+(o.where?'<span class="pc-opt__where">'+esc(o.where)+'</span>':'')+'</li>';}}).join('');
    qList.hidden=false;q.setAttribute('aria-expanded','true');
    if(active>=0)q.setAttribute('aria-activedescendant','q-opt-'+active);else q.removeAttribute('aria-activedescendant');
  }}
  function closeList(){{opts=[];active=-1;render();}}
  function lookup(t){{
    if(t.length<2){{closeList();qStatus.textContent='';return;}}
    var first=clinicMatches(t).concat(local(t));
    lastQuery=t;opts=first;active=-1;render();
    function count(extra){{qStatus.textContent=opts.length?(opts.length+(opts.length===1?' match':' matches')+'. Use the arrow keys to choose one.'+(extra||'')):'No polyclinic or place found yet. Try a nearby village.';}}
    count(' Looking for more addresses…');
    photon(t).then(function(res){{
      if(t!==lastQuery)return;
      var extra=[];res.forEach(function(r){{if(!first.concat(extra).some(function(f){{return f.type==='place'&&samePlace(f,r);}}))extra.push(r);}});
      var keep=active>=0?opts[active]:null;
      opts=first.concat(extra).slice(0,10);active=keep?opts.indexOf(keep):-1;render();count();
    }},function(err){{
      if(err&&err.name==='AbortError')return;if(t!==lastQuery)return;
      count(opts.length?'':' Street addresses are unavailable right now.');
    }});
  }}
  function choose(o){{
    if(!o)return;closeList();
    if(o.type==='clinic'){{location.href=o.slug+'.html';return;}}
    q.value=o.name+(o.where?', '+o.where:'');qStatus.textContent='';
    locBtn.setAttribute('aria-pressed','false');locBtn.textContent='Use my location';locMsg.textContent='';
    setOrigin(o.lat,o.lng,o.name,true);
  }}
  q.addEventListener('input',function(){{
    if(here&&hereLabel&&q.value!==hereLabel)clearOrigin();
    if(opts.length)closeList();clearTimeout(timer);var t=q.value.trim();timer=setTimeout(function(){{lookup(t);}},250);apply();
  }});
  q.addEventListener('keydown',function(ev){{
    if(ev.key==='ArrowDown'||ev.key==='ArrowUp'){{if(!opts.length)return;ev.preventDefault();active+=ev.key==='ArrowDown'?1:-1;
      if(active<0)active=opts.length-1;if(active>=opts.length)active=0;render();}}
    else if(ev.key==='Enter'){{if(active>=0&&opts[active]){{ev.preventDefault();choose(opts[active]);}}}}
    else if(ev.key==='Escape'){{closeList();qStatus.textContent='';}}
  }});
  qList.addEventListener('mousedown',function(ev){{var li=ev.target.closest&&ev.target.closest('.pc-opt');if(!li)return;ev.preventDefault();choose(opts[+li.getAttribute('data-i')]);}});
  document.addEventListener('click',function(ev){{if(!q.contains(ev.target)&&!qList.contains(ev.target))closeList();}});

  /* ---- Use my location */
  var locBtn=document.getElementById('use-location'), locMsg=document.getElementById('location-msg');
  locBtn.addEventListener('click',function(){{
    if(here&&!hereLabel){{clearOrigin();apply();return;}}
    if(!navigator.geolocation){{locMsg.textContent='Your browser cannot share your location. Search by name or place instead.';return;}}
    locMsg.textContent='Finding your location…';
    navigator.geolocation.getCurrentPosition(function(pos){{
      clearOrigin();q.value='';closeList();
      setOrigin(pos.coords.latitude,pos.coords.longitude,'Your location',false);
      locBtn.setAttribute('aria-pressed','true');locBtn.textContent='Stop using my location';
      locMsg.textContent='Showing the nearest first. Distances are in a straight line.';
    }},function(){{locMsg.textContent='We could not get your location. Search by name or place instead.';}},{{timeout:10000}});
  }});

  function paintAll(){{cards.forEach(function(c){{PC.paint(c.querySelector('.pc-status'),JSON.parse(c.dataset.hours));}});}}
  paintAll(); apply();
  setInterval(function(){{paintAll();if(openNow.checked)apply();}},60000);
}})();
</script>
</body>
</html>
'''
    combo_css = """<style>
  /* The live .govbb-form-group is display:flex, so the combobox would not stretch. */
  .pc-combo-group{display:block}
  .pc-combo-group .govbb-label{display:block;margin-bottom:var(--govbb-space-xxs)}
  .pc-combo-group .govbb-hint{display:block;margin:0 0 var(--govbb-space-xs)}
  .pc-combo{position:relative;width:100%} .pc-combo .govbb-input{width:100%;min-width:0}
  .pc-listbox{z-index:1200}
  /* The design system's active-option highlight is 1.22:1 on white; the teal bar is 7.4:1. */
  .pc-opt[aria-selected="true"]{box-shadow:inset 4px 0 0 var(--govbb-teal-80)}
  .pc-opt__name{font-weight:700;display:block;min-width:0;overflow-wrap:anywhere}
  .pc-opt__where{font-size:var(--govbb-font-size-body-sm);color:var(--govbb-color-muted);display:block;min-width:0;overflow-wrap:anywhere}
  #q-status{margin:var(--govbb-space-xxs) 0 0;min-height:1.25rem}
  #area-answer > div{max-inline-size:var(--govbb-measure)} #area-answer p{margin:0} #area-answer p + p{margin-top:var(--govbb-space-xs)}
</style>
"""
    return head('Search for a polyclinic | Government of Barbados',
                'Search for a polyclinic or outpatient clinic in Barbados by name, place or parish, or find the nearest one to you.',
                '../govbb-alpha-styles.css', extra_head=combo_css, dev_notes=FIND_DEV_NOTES) + body


# --------------------------------------------------------------------------- detail pages

def opening_times(s):
    hrs = s.get('hours')
    rows = []
    for i, day in enumerate(DAYS, start=1):
        muted = ''
        if hrs is None:
            val, muted = 'Not confirmed', ' text-grey-70'
        elif hrs.get('allDay'):
            val = 'Open 24 hours'
        elif i in hrs['days']:
            val = f"{fmt(hrs['open'], True)} to {fmt(hrs['close'], True)}"
        else:
            val, muted = 'Closed', ' text-grey-70'
        rows.append(f'<div class="flex items-baseline justify-between gap-s px-xs py-xxs" data-day="{i % 7}"><dt>{day}</dt><dd class="m-0 text-right tabular-nums{muted}">{val}</dd></div>')
    rows.append('<div class="flex items-baseline justify-between gap-s px-xs py-xxs"><dt>Public holidays</dt><dd class="m-0 text-right tabular-nums">Not confirmed. Call before travelling.</dd></div>')
    return '\n          '.join(rows)


def service_list(items):
    return ''.join(f'<li>{e(x)}</li>' for x in items)


def link_to(slug):
    return f'<a class="govbb-link" href="{slug}.html">{e(SITES[slug]["name"])}</a>'


def detail_page(s):
    name = s['name']
    hrs = s.get('hours')
    parent = SITES.get(s.get('parent', ''))
    label, num = call_target(s)

    contact = []
    if s.get('phone'):
        contact.append(f'<dt>Telephone</dt><dd>{tel(s["phone"])}</dd>')
    elif s.get('phoneNote'):
        contact.append(f'<dt>Telephone</dt><dd>{e(s["phoneNote"])}</dd>')
    if s.get('records'):
        contact.append(f'<dt>Medical records</dt><dd>{tel(s["records"])}</dd>')
    if s.get('ehd'):
        contact.append(f'<dt>Environmental health</dt><dd>{tel(s["ehd"])}</dd>')
    if s.get('email'):
        contact.append(f'<dt>Email</dt><dd>{e(s["email"])} <span class="placeholder">[Placeholder address: to be confirmed by the Ministry]</span></dd>')
    contact.append(f'<dt>Address</dt><dd>{e(s["address"])}</dd>')

    hours_intro = ('<p class="govbb-text-body">The clinic\'s opening days and hours have not been confirmed. Only the pharmacy\'s hours are published.</p>'
                   if hrs is None else '')
    urgent = (f'<p class="govbb-text-body"><span class="govbb-text-bold">Urgent care:</span> {e(s["urgent"])}. Call before you go.</p>'
              if s.get('urgent') else '')
    notes = ''.join(f'<p class="govbb-text-body">{e(n)}</p>' for n in s.get('notes', []))

    # services
    if s.get('outpatient'):
        services = (f'<p class="govbb-text-body">This clinic offers a smaller range of services than a polyclinic.'
                    + (f' For anything else, go to {link_to(parent["slug"])}.' if parent else '') + '</p>')
        if s.get('specialist'):
            services += ('<h3 class="govbb-text-h4">Clinics held here</h3><ul class="govbb-list govbb-list--bullet">'
                         + service_list(x['n'] for x in s['specialist']) + '</ul>'
                         '<p class="govbb-text-body-sm pc-muted">Clinic days are not published. Call to check before you go.</p>')
        else:
            services += '<p class="govbb-text-body">The services held here have not been confirmed. Call before you go.</p>'
    else:
        services = ('<p class="govbb-text-body">Like every polyclinic, it offers:</p><ul class="govbb-list govbb-list--bullet pc-cols">'
                    + service_list(DATA['standardServices']) + '</ul>')
        services += '<h3 class="govbb-text-h4">Specialist clinics</h3>'
        if s.get('specialist'):
            services += ('<ul class="govbb-list govbb-list--bullet">' + service_list(x['n'] for x in s['specialist']) + '</ul>'
                         '<p class="govbb-text-body-sm pc-muted">Clinic days are not published. Call to check before you go.</p>')
        else:
            services += '<p class="govbb-text-body">The specialist clinics held here have not been published. Call to check before you go.</p>'
        if s.get('unavailable'):
            services += ('<div class="border-l-4 px-s py-xs border-yellow-80 bg-yellow-20" style="max-inline-size:var(--govbb-measure)"><p class="govbb-text-body"><span class="govbb-text-bold">Not running at present:</span> '
                         + e(', '.join(s['unavailable']).lower().capitalize())
                         + f'. Call the Ministry on {tel(MIN["phone"])} to find out where you can go instead.</p></div>')
        if s.get('satellites'):
            services += ('<h3 class="govbb-text-h4">Outpatient clinics linked to this polyclinic</h3><ul class="govbb-list govbb-list--bullet">'
                         + ''.join(f'<li>{link_to(x)}</li>' for x in s['satellites']) + '</ul>')

    # which areas it serves
    ring = DATA.get('catchments', {}).get(s.get('catchment', ''), {}).get('ring')
    if s.get('servesConfirmed'):
        serves = ('<p class="govbb-text-body">This serves people who live in the Eunice Gibson catchment area. '
                  'The shaded area on the map shows it.</p>')
    else:
        serves = (f'<p class="govbb-text-body">The area this {"clinic" if s.get("outpatient") else "polyclinic"} serves has not been confirmed yet. '
                  f'To find out which polyclinic is for your area, call the Ministry of Health and Wellness on {tel(MIN["phone"])}.</p>')

    # MDA confirmation list (dev notes)
    todo = []
    if s.get('email'):
        todo.append((f'Confirm the email address ({s["email"]} is a placeholder).', 'Contact and help', 'Yes'))
    if hrs is None:
        todo.append(('Confirm the clinic\'s opening days and hours.', 'Opening times, status line, search filters', 'Yes'))
    todo.append(('Confirm public holiday opening.', 'Opening times', 'No'))
    todo.append(('Confirm specialist clinics and their days (the only source is the polyclinics\' unofficial 2023 websites).', 'Services', 'No'))
    if not s.get('servesConfirmed'):
        todo.append(('Confirm which areas this site serves for clinical care (the catchment dataset is only validated for environmental health routing).', 'Which areas it serves', 'No'))
    for n in s.get('mdaNotes', []):
        todo.append((n, 'Various', 'Yes'))
    blocking = any(t[2] == 'Yes' for t in todo)
    dev_rows = '\n'.join(f'     | {q} | {sec} | {b} |' for q, sec, b in todo)
    dev_notes = f'''<!-- DEV NOTES (generated by build_find_a_polyclinic.py from polyclinics.json — edit the data, not this file)
     Status: {"Not publishable yet" if blocking else "Ready for MDA review"}
     To confirm with the Ministry of Health and Wellness:
     | Question | Section it affects | Blocks publishing? |
{dev_rows}
     OUTSIDE SERVICES: unpkg.com (Leaflet map library: receives the visitor's IP address);
     server.arcgisonline.com (Esri map tiles: receives IP address and the map area viewed).
     No personal data is typed on this page. "Get directions" opens Google Maps in the
     user's browser (address text only). Fonts load from alpha.gov.bb.
-->'''

    map_notes = []
    if s.get('pinApprox'):
        map_notes.append('The pin position is approximate.')
    if ring:
        map_notes.append('The shaded area is the Eunice Gibson catchment.')
    map_html = (f'<div id="pc-map" class="pc-map" role="region" aria-label="Map showing where {e(name)} is"></div>'
                + (f'<p class="govbb-text-body-sm pc-muted">{" ".join(map_notes)}</p>' if map_notes else ''))
    map_js = ('<script>(function(){if(!window.L)return;var el=document.getElementById("pc-map");'
              f'var p=[{s["lat"]},{s["lng"]}];'
              'var m=L.map(el,{scrollWheelZoom:false,dragging:!L.Browser.mobile,tap:false,zoomControl:true}).setView(p,15);'
              'L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",'
              '{attribution:"Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, and contributors",minZoom:10,maxZoom:17}).addTo(m);'
              + (f'var r={json.dumps([[pt[1], pt[0]] for pt in ring])};var poly=L.polygon(r,{{color:"#8a7a1a",weight:2,fillColor:"#d9c34a",fillOpacity:.25}}).addTo(m);m.fitBounds(poly.getBounds().extend(p),{{padding:[10,10]}});' if ring else '')
              + f'L.marker(p,{{title:{json.dumps(name)},alt:{json.dumps(name)},keyboard:false}}).addTo(m);'
              '})();</script>')

    body = f'''{breadcrumbs([("Home", "#"), ("Health and emergency services", "#"), ("Find a polyclinic", "../find-a-polyclinic.html"), ("Search for a polyclinic", "find.html")])}
<main id="main-content" tabindex="-1">
  <div class="govbb-width-container govbb-main-wrapper">
    <div class="mb-l flex max-w-2xl flex-col gap-m">
      <div class="flex flex-col gap-xs">
        <h1 class="govbb-text-h1">{e(name)}</h1>
        <div class="border-blue-10 border-b-4 pb-4 text-grey-70"><p class="govbb-text-body-sm">Last updated on {e(DATA["updated"])}.</p></div>
        <div class="min-h-5"><p class="pc-status govbb-text-body-sm govbb-text-bold" data-hours="{e(json.dumps(hrs), quote=True)}" role="status"></p></div>
        <p class="govbb-text-body-sm govbb-text-bold inline-flex w-fit items-center rounded-md px-3 py-1 bg-green-10 text-green-80">{kind(s)}: free health care</p>
        <p class="govbb-text-body">{e(s["address"])}</p>
      </div>
      <div class="flex flex-wrap items-center gap-s">
        <a class="govbb-button" target="_blank" rel="noopener noreferrer" href="{maps_url(s)}">Get directions<span class="govbb-visually-hidden"> (opens in a new tab)</span></a>
        <a class="govbb-button govbb-button--secondary" href="tel:+1{digits(num)}">{e(label)}</a>
      </div>

      <section class="pc-emergency" aria-labelledby="emergency-h">
        <h2 class="govbb-text-h4" id="emergency-h">In an emergency</h2>
        <p class="govbb-text-body">Go to the Queen Elizabeth Hospital’s Accident and Emergency Department, which is open 24 hours a day.</p>
      </section>

      <section aria-labelledby="opening-times" class="pc-section">
        <h2 class="govbb-text-h2" id="opening-times">Opening times</h2>
        {hours_intro}
        <dl class="govbb-text-body m-0 flex flex-col divide-y divide-grey-20" id="pc-hours">
          {opening_times(s)}
        </dl>
        <div class="border-blue-40 border-l-4 bg-blue-10 px-s py-xm"><p class="govbb-text-body"><strong>Public holidays:</strong> polyclinics may close or shorten their hours on public holidays. Call before you go.</p></div>
        {urgent}
        {notes}
      </section>

      <section aria-labelledby="services-h" class="pc-section">
        <h2 class="govbb-text-h2" id="services-h">Services</h2>
        {services}
      </section>

      <section aria-labelledby="pharmacy-h" class="pc-section">
        <h2 class="govbb-text-h2" id="pharmacy-h">Pharmacy</h2>
        <p class="govbb-text-body">The pharmacy has its own opening hours. <a class="govbb-link" href="{PHARMACY}{s["pharmacy"]}">Check the pharmacy’s hours and the prescriptions it accepts</a>.</p>
      </section>

      <section aria-labelledby="location-h" class="pc-section">
        <h2 class="govbb-text-h2" id="location-h">Location</h2>
        {map_html}
        <h3 class="govbb-text-h4">Which areas it serves</h3>
        {serves}
      </section>

      <section aria-labelledby="contact-and-help" class="pc-section">
        <h2 class="govbb-text-h2" id="contact-and-help">Contact and help</h2>
        <dl class="pc-meta">{"".join(contact)}</dl>
        <p class="govbb-text-body">For general questions, contact the Ministry of Health and Wellness on {tel(MIN["phone"])} or {e(MIN["email"])}. If you are overseas, email rather than call.</p>
        <p class="govbb-text-body-sm text-grey-70">Opening hours and services can change. Call ahead to confirm.</p>
      </section>
    </div>
  </div>
  {FEEDBACK}
</main>
{FOOT}
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
{map_js}
<script>
{STATUS_JS}
(function(){{
  var el=document.querySelector('.pc-status'); PC.paint(el,JSON.parse(el.getAttribute('data-hours')));
  var row=document.querySelector('#pc-hours [data-day="'+PC.bbNow().dow+'"]');
  if(row){{row.classList.add('pc-today');row.querySelector('dt').insertAdjacentHTML('afterbegin','<span class="govbb-visually-hidden">Today, </span>');}}
}})();
</script>
</body>
</html>
'''
    return head(f'{name} | Government of Barbados',
                f'Opening times, urgent care, services and contact details for {name}, {s["parish"]}, Barbados.',
                '../govbb-alpha-styles.css',
                extra_head='<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />\n',
                dev_notes=dev_notes) + body


def main():
    out = os.path.join(HERE, 'find-a-polyclinic')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(HERE, 'find-a-polyclinic.html'), 'w', encoding='utf-8') as f:
        f.write(entry_page())
    with open(os.path.join(out, 'find.html'), 'w', encoding='utf-8') as f:
        f.write(find_page())
    for s in DATA['sites']:
        with open(os.path.join(out, s['slug'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(detail_page(s))
    print(f'Built entry, search and {len(DATA["sites"])} detail pages in {HERE}')


if __name__ == '__main__':
    main()

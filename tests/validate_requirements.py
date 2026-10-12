#!/usr/bin/env python3
"""
Requirement validator (v0.2) for the Habits / Planner / Budget / Journal app.

Usage
    pip install playwright && playwright install chromium
    python tests/validate_requirements.py                 # tests ../index.html
    python tests/validate_requirements.py --app path/to/index.html
    python tests/validate_requirements.py --only BUD,PD   # run requirement groups / ids by prefix
    python tests/validate_requirements.py --write-requirements   # regenerate REQUIREMENTS.md
    python tests/validate_requirements.py --chromium /path/to/chromium   # use a specific browser binary

Output (in tests/report/): report.html, report.md, results.json. Exit code is 1 if anything fails.
All network access is blocked except the exchange-rate endpoints, which are mocked per test,
so results do not depend on the internet.
"""
import argparse, json, os, re, sys, time, threading, functools, http.server, datetime as dt, traceback, html
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TZ = 'Europe/London'
NOW = dt.datetime.now(ZoneInfo(TZ))
TODAY = NOW.date()
iso = lambda d: d.isoformat()

# ----------------------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------------------
class Skip(Exception):
    pass

def need(cond, msg='assertion failed'):
    if not cond:
        raise AssertionError(msg)

def eq(a, b, msg=''):
    if a != b:
        raise AssertionError('%s expected %r, got %r' % (msg, b, a))

def seed_data():
    """A realistic data set, relative to today."""
    import random
    random.seed(7)
    T = TODAY
    hab = []
    # streak habit: exactly the last 5 days (incl. today) -> streak 5
    hab.append(dict(id='h0', name='Read 20 pages', icon='\U0001F4DA', color='#3b82f6', type='build', start=iso(T - dt.timedelta(60)),
                    goal=0, saving=0, tags=['mind'], days=[iso(T - dt.timedelta(i)) for i in range(5)]))
    hab.append(dict(id='h1', name='Run', icon='\U0001F3C3', color='#10b981', type='build', start=iso(T - dt.timedelta(60)),
                    goal=0, saving=0, tags=['health'], days=[iso(T - dt.timedelta(i)) for i in range(1, 60) if random.random() < .6]))
    hab.append(dict(id='h2', name='No sugar', icon='\U0001F36C', color='#ef4444', type='quit', start=iso(T - dt.timedelta(20)),
                    goal=30, saving=2, tags=['health'], days=[iso(T - dt.timedelta(9))]))
    tasks = [
        dict(id='t1', title='Gym', date=iso(T - dt.timedelta(10)), time='07:00', dur=60, goal='g1', repeat='weekly', days=[0, 2, 4], until='',
             color='#10b981', tags=['health'], subs=[], done={}, sdone={}),
        dict(id='t3', title='Deep work', date=iso(T), time='10:00', dur=120, goal='', repeat='none', days=[], until='', color='#7c5cff',
             tags=['work'], subs=[dict(id='s1', t='Outline')], done={}, sdone={}),
    ]
    goals = [dict(id='g1', title='Half marathon', start=iso(T - dt.timedelta(30)), end=iso(T + dt.timedelta(90)), color='#10b981')]
    bud = []
    cats = ['groc', 'dining', 'trans', 'bills', 'shop', 'fun', 'health']
    for d in range(0, 200):
        for n in range(random.choice([0, 0, 1, 1, 2])):
            bud.append(dict(id='b%d_%d' % (d, n), date=iso(T - dt.timedelta(d)), cat=random.choice(cats), amt=round(random.uniform(3, 60), 2),
                            cur='GBP', rate=1, note='', tags=random.choice([[], ['work'], ['home']]), repeat='none', until=''))
    bud.append(dict(id='sal', date=iso(T - dt.timedelta(3)), cat='salary', amt=2400, cur='GBP', rate=1, note='Pay', tags=[], repeat='none', until=''))
    bud.append(dict(id='rent', date=iso(T - dt.timedelta(40)), cat='rent', amt=850, cur='GBP', rate=1, note='Rent', tags=['home'], repeat='monthly', until=''))
    plans = [dict(id='p1', name='Car loan', principal=3000, apr=6.9, pay=250, start=iso(T - dt.timedelta(60)), tags=[], extras=[])]
    return dict(app='habit-tracker', version=5, habits=hab, plan=dict(tasks=tasks, goals=goals), journal={}, budget=bud, plans=plans,
                settings=dict(fx=['USD', 'EUR', 'AED']))

FX_OK = {'result': 'success', 'rates': {'USD': 1.30, 'EUR': 1.15, 'INR': 112.5, 'AED': 4.77, 'JPY': 195.2}}

E_ORIGIN = ['http://127.0.0.1:0/']

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

class Env:
    """Owns the browser; hands out fresh pages."""
    def __init__(self, pw, app, chromium):
        kw = dict(args=['--no-sandbox'])
        if chromium:
            kw['executable_path'] = chromium
        self.browser = pw.chromium.launch(**kw)
        self.path = str(Path(app).resolve())
        self.file_url = 'file://' + self.path
        # serve the app over http like GitHub Pages does (storage behaves like a real site, and is reliable in headless Chromium)
        handler = functools.partial(QuietHandler, directory=str(Path(self.path).parent))
        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.app = 'http://127.0.0.1:%d/%s' % (self.srv.server_address[1], Path(self.path).name)
        self.origin = 'http://127.0.0.1:%d/' % self.srv.server_address[1]
        self.pages = []
        E_ORIGIN[0] = self.origin

    def page(self, w=390, h=844, seed=True, fx='ok', init='', ctx_kw=None, wait=450, goto=True):
        """fx: 'ok' (mock success) | 'fail' (all sources fail) | 'second' (first source fails) | 'noaed' | None (blocked)"""
        ctx = self.browser.new_context(viewport=dict(width=w, height=h), timezone_id=TZ, accept_downloads=True, **(ctx_kw or {}))
        if seed is True:
            seed = seed_data()
        if seed:
            ctx.add_init_script("if(!localStorage.getItem('ht_data')&&!sessionStorage.getItem('seeded')){localStorage.setItem('ht_data',%s);sessionStorage.setItem('seeded','1')}" % json.dumps(json.dumps(seed)))
        if init:
            ctx.add_init_script(init)
        pg = ctx.new_page()
        pg.errs, pg.reqs, pg.dialogs = [], [], []
        pg.on('pageerror', lambda e: pg.errs.append(str(e)))
        pg.on('console', lambda m: pg.errs.append(m.text) if m.type == 'error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        pg.on('dialog', lambda d: (pg.dialogs.append(d.message), d.accept()))

        def route(r):
            u = r.request.url
            if u.startswith(('file:', 'data:', 'blob:')) or u.startswith(E_ORIGIN[0]):
                return r.continue_()
            pg.reqs.append(u)
            if fx and 'open.er-api' in u and fx in ('ok', 'noaed'):
                rates = dict(FX_OK['rates'])
                if fx == 'noaed':
                    rates.pop('AED')
                return r.fulfill(status=200, content_type='application/json', body=json.dumps({'rates': rates}))
            if fx == 'second' and 'frankfurter' in u:
                return r.fulfill(status=200, content_type='application/json', body=json.dumps({'rates': FX_OK['rates']}))
            return r.abort()
        pg.route('**/*', route)
        pg._ctx = ctx
        self.pages.append(ctx)
        if goto:
            pg.goto(self.app)
            pg.wait_for_timeout(wait)
        return pg

    def close_all(self):
        for c in self.pages:
            try: c.close()
            except Exception: pass
        self.pages = []

    def close(self):
        self.browser.close(); self.srv.shutdown()

# page-level helpers -------------------------------------------------------------------------
def nav(pg, name):
    pg.click('#ttl'); pg.click('#pgPop button:text-is("%s")' % name); pg.wait_for_timeout(250)

def tab(pg, sel, t):
    pg.click('%s [data-t=%s]' % (sel, t)); pg.wait_for_timeout(200)

def data(pg):
    raw = pg.evaluate("localStorage.getItem('ht_data')")
    return json.loads(raw) if raw else dict(habits=[], plan=dict(tasks=[], goals=[]), journal={}, budget=[], plans=[], settings={})

def no_overflow(pg):
    return pg.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1")

def rgb(s):
    m = re.findall(r'[\d.]+', s)
    return [float(x) for x in m[:3]]

def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= .03928 else ((v / 255 + .055) / 1.055) ** 2.4
    r, g, b = [f(x) for x in c]
    return .2126 * r + .7152 * g + .0722 * b

def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)

def add_habit(pg, name, quit_=False, tags=''):
    pg.click('#addBtn'); pg.wait_for_timeout(250)
    pg.fill('#mName', name)
    if tags: pg.fill('#mTags', tags)
    if quit_:
        pg.click('#tSeg [data-t=quit]'); pg.wait_for_timeout(100)
    pg.click('#mOk'); pg.wait_for_timeout(300)

def add_entry(pg, amt, cat=None, kind=None, note='', repeat=None, tags=''):
    pg.click('#addBtn'); pg.wait_for_timeout(250)
    if kind: pg.click('#txK [data-k=%s]' % kind)
    pg.fill('#txA', str(amt))
    if cat: pg.locator('#txCats .cp', has_text=cat).first.click()
    if note: pg.fill('#txN', note)
    if tags: pg.fill('#txTg', tags)
    if repeat: pg.select_option('#txRp', repeat)
    pg.click('#txOk'); pg.wait_for_timeout(300)

ALL_VIEWS = [('habits', '#tabs', ['list', 'week', 'month', 'day', 'year', 'stats']),
             ('planner', '#ptabs', ['day', 'rolling', 'week', 'goals', 'stats']),
             ('budget', '#btabs', ['week', 'month', 'year']),
             ('journal', None, [])]
PAGE_NAME = {'habits': 'Habits', 'planner': 'Planner', 'budget': 'Budget', 'journal': 'Journal'}

def walk_views(pg, fn):
    """Visit every page and tab, calling fn(label)."""
    for p, sel, tabs in ALL_VIEWS:
        nav(pg, PAGE_NAME[p])
        if not tabs:
            fn(p)
        for t in tabs:
            tab(pg, sel, t); fn('%s/%s' % (p, t))

# ----------------------------------------------------------------------------------------------
# requirement catalogue + tests
# ----------------------------------------------------------------------------------------------
REQS = []   # (id, area, text, func)
AREAS = {
    'GEN': 'General, platform and look', 'DAT': 'Data storage, export and import', 'RSP': 'UI resizing and responsiveness',
    'HAB': 'Habit tracker', 'PLN': 'Planner and goals', 'BUD': 'Budget tracker', 'JRN': 'Journal, hourly mood, emotion wheel, weight and calories',
    'PD': 'Passive / automatic data (clock, timer, exchange rates, derived figures)',
}

def req(rid, text):
    def deco(fn):
        REQS.append((rid, rid.split('-')[0], text, fn))
        return fn
    return deco

# ============================== GEN ==============================
@req('GEN-01', 'The app is one self-contained HTML file: apart from exchange-rate lookups it makes no network requests, and needs no CSS/JS/font files.')
def _(E):
    pg = E.page(fx=None)
    walk_views(pg, lambda l: None)
    bad = [u for u in pg.reqs if not re.search(r'open\.er-api|frankfurter|currency-api', u)]
    need(not bad, 'unexpected requests: %s' % bad[:3])
    src = Path(E.path).read_text(encoding='utf-8')
    need(not re.search(r'<link[^>]+rel=["\']stylesheet', src), 'external stylesheet found')
    need(not re.search(r'<script[^>]+src=', src), 'external script found')

@req('GEN-02', 'No JavaScript or console errors occur on any page or tab (phone and laptop size).')
def _(E):
    for w, h in [(390, 844), (1280, 860)]:
        pg = E.page(w, h)
        walk_views(pg, lambda l: None)
        need(not pg.errs, 'errors at %dpx: %s' % (w, pg.errs[:2]))

@req('GEN-03', 'The app loads and its buttons work with the network completely offline.')
def _(E):
    pg = E.page(fx=None)
    pg.click('#addBtn'); pg.wait_for_timeout(250)
    need(pg.locator('#modal.open').count() == 1, 'add sheet did not open')
    pg.click('#mCancel'); pg.wait_for_timeout(350)
    nav(pg, 'Budget')
    need(pg.locator('#bSum .tile').count() == 4, 'budget tiles missing')

@req('GEN-04', 'The Barlow Condensed font is embedded in the file (works offline, nothing fetched from Google).')
def _(E):
    pg = E.page(fx=None)
    src = Path(E.path).read_text(encoding='utf-8')
    need('fonts.googleapis' not in src, 'still references Google Fonts')
    need(len(re.findall(r'@font-face', src)) >= 3, 'fewer than 3 embedded faces')
    need(pg.evaluate("document.fonts.check('16px \"Barlow Condensed\"')"), 'font not available')

@req('GEN-05', 'Apple/mobile support: viewport meta with safe-area, apple-mobile-web-app meta tags and theme colour are present.')
def _(E):
    pg = E.page()
    need('viewport-fit=cover' in pg.evaluate("document.querySelector('meta[name=viewport]').content"), 'viewport-fit')
    for m in ['apple-mobile-web-app-capable', 'apple-mobile-web-app-title', 'theme-color']:
        need(pg.locator('meta[name=%s]' % m).count() == 1, m + ' missing')

@req('GEN-06', 'Dark theme: very dark page background and light text.')
def _(E):
    pg = E.page()
    bg = rgb(pg.evaluate("getComputedStyle(document.body).backgroundColor"))
    fg = rgb(pg.evaluate("getComputedStyle(document.body).color"))
    need(lum(bg) < .02, 'background not dark: %s' % bg)
    need(contrast(bg, fg) > 7, 'low text contrast')

@req('GEN-07', 'No bold fonts: no visible element uses a font weight above 500, on any page.')
def _(E):
    pg = E.page()
    worst = []
    def chk(l):
        w = pg.evaluate("""[...document.querySelectorAll('body *')].filter(e=>e.offsetParent!==null&&e.textContent.trim()).map(e=>+getComputedStyle(e).fontWeight).filter(x=>x>500).length""")
        if w: worst.append((l, w))
    walk_views(pg, chk)
    need(not worst, 'bold text on %s' % worst[:3])

@req('GEN-08', 'Buttons use drawn icons or text, never emoji (habit icon picker excluded).')
def _(E):
    pg = E.page()
    emoji = re.compile('[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2B06\u2714\u2705]')
    bad = []
    def chk(l):
        for t in pg.evaluate("[...document.querySelectorAll('button')].filter(b=>b.offsetParent!==null&&!b.closest('#emos,.ico')).map(b=>b.textContent)"):
            if emoji.search(t): bad.append((l, t))
    walk_views(pg, chk)
    nav(pg, 'Habits'); pg.click('#addBtn'); pg.wait_for_timeout(250)
    for t in pg.evaluate("[...document.querySelectorAll('#modal button')].filter(b=>!b.closest('#emos')).map(b=>b.textContent)"):
        if emoji.search(t): bad.append(('sheet', t))
    need(not bad, 'emoji in buttons: %s' % bad[:3])

@req('GEN-09', 'Page switcher lists Habits, Planner, Budget and Journal, and the chosen page is remembered after reload.')
def _(E):
    pg = E.page()
    pg.click('#ttl'); pg.wait_for_timeout(150)
    eq(pg.locator('#pgPop button').all_inner_texts(), ['Habits', 'Planner', 'Budget', 'Journal'])
    pg.click('#pgPop button:text-is("Budget")'); pg.wait_for_timeout(200)
    pg.reload(); pg.wait_for_timeout(450)
    eq(pg.inner_text('#ttlT'), 'Budget')
    need(pg.title().startswith('Budget'), 'document title: ' + pg.title())

@req('GEN-10', 'Footer carries a very small, subtle disclaimer (no responsibility, no data collected, free to use) and "v0.2" at the bottom right.')
def _(E):
    pg = E.page()
    need(pg.locator('footer.ft').count() == 1, 'no footer')
    txt = pg.inner_text('footer.ft').lower()
    for w in ['without warranty', 'no responsibility', 'no data is collected', 'free to use', 'v0.2']:
        need(w in txt, 'footer missing: ' + w)
    fs = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('footer.ft')).fontSize)")
    need(fs <= 11, 'footer font too large: %s' % fs)
    r = pg.evaluate("(()=>{const f=document.querySelector('footer.ft').getBoundingClientRect(),v=document.querySelector('footer.ft span').getBoundingClientRect();return {fr:f.right,vr:v.right,vl:v.left,fl:f.left}})()")
    need(r['vl'] > r['fl'] + (r['fr'] - r['fl']) * .5 and r['fr'] - r['vr'] < 40, 'version not at right: %s' % r)
    col = rgb(pg.evaluate("getComputedStyle(document.querySelector('footer.ft')).color"))
    need(max(col) < 140, 'footer colour not subtle')

@req('GEN-11', 'If browser storage is blocked the app still loads and works in memory without errors.')
def _(E):
    pg = E.page(seed=False, init="Object.defineProperty(window,'localStorage',{get(){throw new Error('denied')}})")
    add_habit(pg, 'Memory only')
    need(pg.locator('.habit').count() == 1, 'habit not created')
    need(not pg.errs, 'errors: %s' % pg.errs[:2])

@req('GEN-12', 'Add button (+) is available on Habits, Planner and Budget and hidden on Journal; each opens the right sheet.')
def _(E):
    pg = E.page()
    pg.click('#addBtn'); need(pg.locator('#modal.open').count() == 1); pg.click('#mCancel'); pg.wait_for_timeout(300)
    nav(pg, 'Planner'); pg.click('#addBtn'); need(pg.locator('#taskM.open').count() == 1); pg.click('#tkCancel'); pg.wait_for_timeout(300)
    tab(pg, '#ptabs', 'goals'); pg.click('#addBtn'); need(pg.locator('#goalM.open').count() == 1); pg.click('#glCancel'); pg.wait_for_timeout(300)
    nav(pg, 'Budget'); pg.click('#addBtn'); need(pg.locator('#txM.open').count() == 1); pg.click('#txCancel'); pg.wait_for_timeout(300)
    nav(pg, 'Journal'); need(not pg.is_visible('#addBtn'), 'add button visible on journal')

@req('GEN-13', 'Works the same when the file is opened directly from disk (file://) and when hosted over http(s) as on GitHub Pages.')
def _(E):
    pg = E.page(goto=False, seed=False)
    pg.goto(E.file_url); pg.wait_for_timeout(500)
    add_habit(pg, 'From disk'); eq(pg.locator('.habit .name').all_inner_texts(), ['From disk'])
    need(not pg.errs, str(pg.errs))
    pg2 = E.page(seed=False); add_habit(pg2, 'Hosted'); eq(pg2.locator('.habit .name').all_inner_texts(), ['Hosted'])

# ============================== DAT ==============================
@req('DAT-01', 'Auto-save: every change is written to browser storage as one JSON document (habits, plan, journal, budget, plans, settings).')
def _(E):
    pg = E.page(seed=False)
    add_habit(pg, 'Water')
    d = data(pg)
    for k in ['habits', 'plan', 'journal', 'budget', 'plans', 'settings']:
        need(k in d, 'missing key ' + k)
    eq([h['name'] for h in d['habits']], ['Water'])

@req('DAT-02', 'Reloading restores habits, planner, journal, budget and payment plans from storage.')
def _(E):
    pg = E.page()
    pg.evaluate("jr['%s']={m:4,g:'tea',t:'hello world'};saveJ()" % iso(TODAY))
    pg.reload(); pg.wait_for_timeout(450)
    d = data(pg)
    need(len(d['habits']) == 3 and len(d['budget']) > 50 and len(d['plans']) == 1 and len(d['plan']['tasks']) == 2, 'data lost')
    nav(pg, 'Journal')
    need(pg.input_value('#jt') == 'hello world', 'journal text not restored')

@req('DAT-03', 'Export file: Data menu downloads a .json file containing all data.')
def _(E):
    pg = E.page()
    pg.click('#dataBtn'); pg.wait_for_timeout(250)
    with pg.expect_download() as dl:
        pg.click('#expBtn')
    f = dl.value
    need(f.suggested_filename.endswith('.json'), f.suggested_filename)
    j = json.loads(Path(f.path()).read_text(encoding='utf-8'))
    need(len(j['habits']) == 3 and 'budget' in j and 'plan' in j and 'journal' in j, 'export incomplete')

@req('DAT-04', 'Import file: choosing a valid export replaces the current data.')
def _(E):
    pg = E.page(seed=False)
    tmp = HERE / 'report' / '_import.json'
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(json.dumps(seed_data()), encoding='utf-8')
    pg.click('#dataBtn'); pg.wait_for_timeout(250)
    pg.set_input_files('#fileIn', str(tmp)); pg.wait_for_timeout(500)
    eq(len(data(pg)['habits']), 3)
    tmp.unlink()

@req('DAT-05', 'Import rejects an invalid file with a message and leaves existing data untouched.')
def _(E):
    pg = E.page()
    tmp = HERE / 'report' / '_bad.json'
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text('{"hello":1}', encoding='utf-8')
    pg.click('#dataBtn'); pg.wait_for_timeout(250)
    pg.set_input_files('#fileIn', str(tmp)); pg.wait_for_timeout(400)
    need(any('could not be read' in d for d in pg.dialogs), 'no error message: %s' % pg.dialogs)
    eq(len(data(pg)['habits']), 3)
    tmp.unlink()

@req('DAT-06', 'Budget-only export produces a CSV (with header and one row per entry); the other data is not included.')
def _(E):
    pg = E.page()
    n = pg.evaluate("bud.length")
    with pg.expect_download() as dl:
        pg.evaluate("expBud()")
    f = dl.value
    need(f.suggested_filename.endswith('.csv'), f.suggested_filename)
    txt = Path(f.path()).read_text(encoding='utf-8-sig')
    lines = [l for l in txt.strip().splitlines() if l]
    need(lines[0].startswith('date,type,category'), 'header: ' + lines[0])
    eq(len(lines) - 1, n, 'row count')
    need('habit' not in lines[0].lower(), 'non-budget columns')

@req('DAT-07', 'Settings persist across reloads: habit view, sort order, week start day, exchange-rate currencies, Pomodoro lengths, budget period.')
def _(E):
    pg = E.page()
    pg.click('#tabs [data-t=month]'); pg.click('#sBtn'); pg.click('#sPop button >> nth=1'); pg.wait_for_timeout(150)
    sort = pg.evaluate("localStorage.getItem('ht_sort')")
    nav(pg, 'Planner'); tab(pg, '#ptabs', 'week'); pg.select_option('#wsSel', '6')
    pg.click('#fxBtn'); pg.select_option('#fx1', 'JPY')
    pg.click('#psBtn'); pg.evaluate("(()=>{const r=document.querySelector('#fr');r.value=40;r.dispatchEvent(new Event('input'))})()")
    pg.mouse.click(5, 400)
    nav(pg, 'Budget'); tab(pg, '#btabs', 'year')
    pg.reload(); pg.wait_for_timeout(500)
    eq(pg.evaluate("localStorage.getItem('ht_view2')"), 'month')
    eq(pg.evaluate("localStorage.getItem('ht_sort')"), sort)
    eq(pg.evaluate("localStorage.getItem('ht_ws')"), '6')
    eq(pg.evaluate("JSON.parse(localStorage.getItem('ht_fxpick'))[0]"), 'JPY')
    eq(pg.inner_text('#pt'), '40:00')
    eq(pg.evaluate("localStorage.getItem('ht_bper')"), 'year')

# ============================== RSP ==============================
WIDTHS = [(320, 640), (360, 740), (390, 844), (430, 932), (768, 1024), (1024, 768), (1280, 860), (1920, 1080)]
def _mk_overflow(w, h):
    def fn(E):
        pg = E.page(w, h)
        bad = []
        def chk(l):
            if not no_overflow(pg): bad.append(l)
        walk_views(pg, chk)
        pg.click('#addBtn') if False else None
        need(not bad, 'horizontal scroll at %dpx on: %s' % (w, bad))
    return fn
for _w, _h in WIDTHS:
    req('RSP-%02d' % (WIDTHS.index((_w, _h)) + 1), 'No sideways page scroll on any page or tab at %d px wide.' % _w)(_mk_overflow(_w, _h))

@req('RSP-09', 'Live resizing: shrinking from laptop to phone width and back re-flows the layout with no sideways scroll and no reload.')
def _(E):
    pg = E.page(1280, 860)
    for p, sel, tabs in ALL_VIEWS:
        nav(pg, PAGE_NAME[p])
        for w, h in [(390, 844), (1280, 860), (360, 640)]:
            pg.set_viewport_size(dict(width=w, height=h)); pg.wait_for_timeout(150)
            need(no_overflow(pg), 'overflow on %s at %d' % (p, w))

@req('RSP-10', 'Pomodoro timer stays on a single row from 320 px upward; the three exchange rates stay on one line from 360 px upward.')
def _(E):
    for w in [320, 360, 390, 768, 1280]:
        pg = E.page(w, 800)
        h = pg.evaluate("document.querySelector('#pomo').getBoundingClientRect().height")
        need(h < 64, 'pomodoro wraps at %d (height %s)' % (w, h))
        if w >= 360:
            tops = pg.evaluate("[...document.querySelectorAll('#fxr > span, #fxv span')].map(e=>Math.round(e.getBoundingClientRect().top/4))")
            need(len(set(tops)) == 1, 'rate line wraps at %d: %s' % (w, tops))
            r = pg.evaluate("[...document.querySelectorAll('#fxv span')].map(e=>e.getBoundingClientRect().right).pop()<=innerWidth")
            need(r, 'rates run off screen at %d' % w)

@req('RSP-11', 'Budget summary shows income, expense, savings and left in a single row at every width from 320 px.')
def _(E):
    for w in [320, 360, 390, 768, 1280]:
        pg = E.page(w, 800); nav(pg, 'Budget')
        tops = pg.evaluate("[...document.querySelectorAll('#bSum .tile')].map(e=>Math.round(e.getBoundingClientRect().top))")
        need(len(tops) == 4 and len(set(tops)) == 1, 'tiles on several rows at %d: %s' % (w, tops))

@req('RSP-12', 'Habit year view fits without side scrolling on phones.')
def _(E):
    for w in [320, 360, 390]:
        pg = E.page(w, 800); tab(pg, '#tabs', 'year')
        r = pg.evaluate("[...document.querySelectorAll('.yg')].map(e=>[e.scrollWidth,e.clientWidth])")
        need(r and all(a <= b + 1 for a, b in r), 'year grid scrolls at %d: %s' % (w, r[:1]))
        need(no_overflow(pg), 'page overflow')

@req('RSP-13', 'Weekly planner shows 3 days by default on phones and 7 on laptops, and the user can change the count.')
def _(E):
    pg = E.page(390, 844); eq(pg.evaluate("wDays"), 3)
    pg2 = E.page(1280, 860); eq(pg2.evaluate("wDays"), 7)
    nav(pg2, 'Planner'); tab(pg2, '#ptabs', 'rolling')
    n = pg2.locator('.wbar button, .gbar button').count()
    need(pg2.evaluate("document.querySelectorAll('[data-n]').length") >= 2, 'no day-count selector')

@req('RSP-14', 'Sheets/dialogs: bottom sheet on phones, centred dialog on laptops; always fully inside the viewport and scrollable.')
def _(E):
    pg = E.page(390, 700)
    pg.click('#addBtn'); pg.wait_for_timeout(450)
    r = pg.evaluate("(()=>{const s=document.querySelector('#modal .sheet').getBoundingClientRect();return {b:s.bottom,t:s.top,h:innerHeight}})()")
    need(abs(r['b'] - r['h']) < 3, 'not docked at bottom: %s' % r)
    need(r['t'] >= 0, 'sheet taller than viewport')
    pg2 = E.page(1280, 860)
    pg2.click('#addBtn'); pg2.wait_for_timeout(450)
    r = pg2.evaluate("(()=>{const s=document.querySelector('#modal .sheet').getBoundingClientRect();return {t:s.top,b:s.bottom,h:innerHeight}})()")
    need(r['t'] > 20 and r['h'] - r['b'] > 20, 'not centred: %s' % r)
    for w, h in [(360, 600), (320, 560)]:
        pg3 = E.page(w, h); nav(pg3, 'Budget'); pg3.click('#addBtn'); pg3.wait_for_timeout(450)
        r = pg3.evaluate("(()=>{const s=document.querySelector('#txM .sheet'),b=s.getBoundingClientRect();return {t:b.top,b:b.bottom,h:innerHeight,sc:s.scrollHeight>s.clientHeight,ov:getComputedStyle(s).overflowY}})()")
        need(r['t'] >= 0 and r['b'] <= r['h'] + 1, 'sheet outside viewport at %dx%d: %s' % (w, h, r))
        need(not r['sc'] or r['ov'] in ('auto', 'scroll'), 'tall sheet not scrollable')

@req('RSP-15', 'Touch-friendly: main tap targets (tabs, tick buttons, toolbar buttons, + button) are at least 28 px high; form fields use 16 px text so iOS does not zoom.')
def _(E):
    pg = E.page(390, 844)
    small = pg.evaluate("[...document.querySelectorAll('#tabs button,.chk,.tb,#addBtn')].filter(b=>b.offsetParent!==null).map(b=>b.getBoundingClientRect().height).filter(h=>h<28).length")
    eq(small, 0, 'small targets')
    pg.click('#addBtn'); pg.wait_for_timeout(300)
    fs = pg.evaluate("[...document.querySelectorAll('#modal input[type=text],#modal input[type=number],#modal input[type=date]')].map(e=>parseFloat(getComputedStyle(e).fontSize)).filter(x=>x<16).length")
    eq(fs, 0, 'inputs under 16px')

@req('RSP-16', 'The + button stays inside the viewport at every width and the page keeps room below the content so it never hides the footer text.')
def _(E):
    for w, h in WIDTHS:
        pg = E.page(w, h)
        r = pg.evaluate("(()=>{const b=document.querySelector('#addBtn').getBoundingClientRect();return [b.left>=0,b.right<=innerWidth,b.top>=0,b.bottom<=innerHeight]})()")
        need(all(r), 'fab outside viewport at %d: %s' % (w, r))
        pg.evaluate("window.scrollTo(0,document.body.scrollHeight)"); pg.wait_for_timeout(100)
        o = pg.evaluate("(()=>{const f=document.querySelector('footer.ft').getBoundingClientRect(),b=document.querySelector('#addBtn').getBoundingClientRect();return !(b.left<f.right&&b.right>f.left&&b.top<f.bottom&&b.bottom>f.top)})()")
        need(o, 'fab covers footer at %d' % w)

@req('RSP-17', 'Content is centred and capped to a readable maximum width on very wide screens.')
def _(E):
    pg = E.page(1920, 1080)
    r = pg.evaluate("(()=>{const b=document.querySelector('.wrap').getBoundingClientRect();return [b.width,b.left,innerWidth-b.right]})()")
    need(r[0] <= 1200 and abs(r[1] - r[2]) < 3, 'wrap not capped/centred: %s' % r)

@req('RSP-18', 'Habit cards use a multi-column grid on laptops and a single column on phones.')
def _(E):
    pg = E.page(390, 844)
    need(pg.evaluate("new Set([...document.querySelectorAll('.habit')].map(e=>e.getBoundingClientRect().left)).size")==1, 'phone not single column')
    pg2 = E.page(1280, 860)
    need(pg2.evaluate("new Set([...document.querySelectorAll('.habit')].map(e=>Math.round(e.getBoundingClientRect().left))).size")>=2, 'laptop not multi column')

# ============================== HAB ==============================
@req('HAB-01', 'Habit views are tabs along the top in the order List (default), Week, Month, Day, Year, Statistics.')
def _(E):
    pg = E.page()
    eq(pg.locator('#tabs button').all_inner_texts(), ['List', 'Week', 'Month', 'Day', 'Year', 'Statistics'])
    eq(pg.locator('#tabs button.on').inner_text(), 'List')
    need(pg.locator('#vBtn').count() == 0, 'old view popover still present')

@req('HAB-02', 'Add a build habit with name, tags, icon and colour; it appears in the list and the header counts it.')
def _(E):
    pg = E.page(seed=False)
    eq(pg.inner_text('#sub'), 'Nothing tracked yet')
    add_habit(pg, 'Stretch', tags='morning')
    eq(pg.locator('.habit .name').all_inner_texts(), ['Stretch'])
    eq(pg.inner_text('#sub'), '0 of 1 done today')

@req('HAB-03', 'Ticking a habit today updates the header ("1 of 1 done"), the streak text and storage; ticking again undoes it.')
def _(E):
    pg = E.page(seed=False); add_habit(pg, 'Stretch')
    pg.click('.habit .chk'); pg.wait_for_timeout(300)
    eq(pg.inner_text('#sub'), '1 of 1 done today')
    need(iso(TODAY) in data(pg)['habits'][0]['days'], 'day not saved')
    need('1' in pg.inner_text('.habit .meta'), 'streak not shown: ' + pg.inner_text('.habit .meta'))
    pg.click('.habit .chk'); pg.wait_for_timeout(300)
    eq(pg.inner_text('#sub'), '0 of 1 done today')

@req('HAB-04', 'Quit habits: quit date, goal days and money saved per day; days since the quit date count as clean; tapping today logs a slip and restarts the streak.')
def _(E):
    pg = E.page(seed=False)
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.click('#tSeg [data-t=quit]'); pg.wait_for_timeout(150)
    need(pg.is_visible('#quitF'), 'quit fields hidden')
    pg.fill('#mName', 'No sugar'); pg.fill('#mStart', iso(TODAY - dt.timedelta(6))); pg.fill('#mGoal', '30'); pg.fill('#mSave', '2'); pg.click('#mOk'); pg.wait_for_timeout(300)
    eq(pg.evaluate("streak(habits[0])"), 7)
    eq(pg.inner_text('#sub'), '1 of 1 done today')
    pg.click('.habit .chk'); pg.wait_for_timeout(300)
    eq(pg.evaluate("streak(habits[0])"), 0)
    eq(pg.inner_text('#sub'), '0 of 1 done today')
    need(pg.locator('.habit .bar').count() == 1, 'goal progress bar missing')

@req('HAB-05', 'Tapping a habit name opens it for editing; Delete (after confirming) removes it.')
def _(E):
    pg = E.page()
    pg.click('.habit .info >> nth=0'); pg.wait_for_timeout(250)
    eq(pg.input_value('#mName'), 'Read 20 pages')
    pg.fill('#mName', 'Read 30 pages'); pg.click('#mOk'); pg.wait_for_timeout(250)
    need('Read 30 pages' in pg.locator('.habit .name').all_inner_texts(), 'rename failed')
    pg.click('.habit .info >> nth=0'); pg.wait_for_timeout(250); pg.click('#mDel'); pg.wait_for_timeout(300)
    eq(len(data(pg)['habits']), 2)

@req('HAB-06', 'Tags: tag chips filter the list; typing in the tag field suggests existing tags.')
def _(E):
    pg = E.page()
    chips = pg.locator('#chips .chip').all_inner_texts()
    need(set(['health', 'mind']) <= set(c.lower() for c in chips), 'tag chips: %s' % chips)
    pg.locator('#chips .chip', has_text='mind').click(); pg.wait_for_timeout(250)
    eq(pg.locator('.habit').count(), 1)
    pg.locator('#chips .chip').first.click(); pg.wait_for_timeout(250)
    eq(pg.locator('.habit').count(), 3)
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#mTags', 'he'); pg.wait_for_timeout(150)
    need('health' in pg.inner_text('#tagSug'), 'no tag suggestion')

@req('HAB-07', 'Sort button offers several orders and reorders the list (e.g. by name).')
def _(E):
    pg = E.page()
    pg.click('#sBtn'); pg.wait_for_timeout(150)
    opts = pg.locator('#sPop button').all_inner_texts()
    need(len(opts) >= 4, 'sort options: %s' % opts)
    name = [o for o in opts if 'name' in o.lower()]
    need(name, 'no name sort')
    pg.click('#sPop button:text-is("%s")' % name[0]); pg.wait_for_timeout(300)
    names = pg.locator('.habit .name').all_inner_texts()
    eq(names, sorted(names, key=str.lower))

@req('HAB-08', 'Week, Month and Day views each show their own visualisation and the previous/next arrows change the period.')
def _(E):
    pg = E.page(); seen = {}
    for t in ['week', 'month', 'day', 'year']:
        tab(pg, '#tabs', t)
        seen[t] = pg.evaluate("document.querySelector('#hviz').innerHTML.length+'|'+document.querySelector('#list').innerHTML.length")
        need(pg.locator('.habit').count() == 3, t + ' lost habits')
    need(len(set(seen.values())) == 4, 'views not distinct')
    tab(pg, '#tabs', 'month')
    a = pg.inner_text('#navBox')
    pg.click('#navBox .nav button >> nth=0'); pg.wait_for_timeout(250)
    need(pg.inner_text('#navBox') != a, 'month did not change')

@req('HAB-09', 'Year view shows 12 month rows with one cell per day for every habit.')
def _(E):
    pg = E.page(1280, 860); tab(pg, '#tabs', 'year')
    n = pg.evaluate("document.querySelectorAll('.habit')[0].querySelectorAll('.yg .cell:not([style*=hidden])').length")
    yr = TODAY.year; days = 366 if (yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0)) else 365
    eq(n, days, 'cells')
    eq(pg.evaluate("document.querySelectorAll('.habit')[0].querySelectorAll('.yg .ml').length"), 12)

@req('HAB-10', 'Statistics tab shows overview tiles and per-habit benchmark metrics.')
def _(E):
    pg = E.page(); tab(pg, '#tabs', 'stats')
    need(pg.is_visible('#stats'), 'stats hidden')
    need(pg.locator('#stats .tile').count() >= 4, 'few tiles')
    txt = pg.inner_text('#stats').lower()
    for w in ['streak', 'rate']:
        need(w in txt, 'missing metric: ' + w)

@req('HAB-11', 'Streak maths: a habit ticked on the last 5 consecutive days (incl. today) has a streak of 5; a gap resets it.')
def _(E):
    pg = E.page()
    eq(pg.evaluate("streak(habits[0])"), 5)
    pg.evaluate("habits[0].days.delete('%s')" % iso(TODAY - dt.timedelta(2)))
    eq(pg.evaluate("streak(habits[0])"), 2)

# ============================== PLN ==============================
@req('PLN-01', 'Planner tabs: Day, Rolling, Week, Goals, Statistics, in that order.')
def _(E):
    pg = E.page(); nav(pg, 'Planner')
    eq(pg.locator('#ptabs button').all_inner_texts(), ['Day', 'Rolling', 'Week', 'Goals', 'Statistics'])

@req('PLN-02', 'Add a one-off task and complete it: it shows in the day list, the header reads "x of y tasks done today", and ticking updates it.')
def _(E):
    pg = E.page(seed=False); nav(pg, 'Planner')
    eq(pg.inner_text('#sub'), 'No tasks today')
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#tkT', 'Buy milk'); pg.click('#tkOk'); pg.wait_for_timeout(300)
    eq(pg.inner_text('#sub'), '0 of 1 tasks done today')
    pg.click('.task .chk'); pg.wait_for_timeout(300)
    eq(pg.inner_text('#sub'), '1 of 1 tasks done today')

@req('PLN-03', 'Recurring tasks: repeat Once / Daily / chosen weekdays / Monthly; the weekday picker defaults to the current weekday and tasks only occur on the chosen days.')
def _(E):
    pg = E.page(seed=False); nav(pg, 'Planner')
    pg.click('#addBtn'); pg.wait_for_timeout(250)
    eq(pg.locator('#tkR button').all_inner_texts(), ['Once', 'Daily', 'Days', 'Monthly'])
    pg.fill('#tkT', 'Standup'); pg.click('#tkR [data-r=weekly]'); pg.wait_for_timeout(150)
    on = pg.evaluate("[...document.querySelectorAll('#tkDays button.on')].map(b=>b.textContent)")
    eq(on, [['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][(TODAY.weekday())]], 'default day')
    for d in on: pg.click('#tkDays button:text-is("%s")' % d)
    pg.click('#tkDays button:text-is("Tue")'); pg.click('#tkDays button:text-is("Thu")'); pg.click('#tkOk'); pg.wait_for_timeout(300)
    days = [TODAY + dt.timedelta(i) for i in range(14)]
    got = pg.evaluate("(ds)=>ds.filter(d=>dayAll(d).length).map(d=>d)", [iso(d) for d in days])
    eq(got, [iso(d) for d in days if d.weekday() in (1, 3)])

@req('PLN-04', 'Monthly repeat occurs on the same date each month.')
def _(E):
    pg = E.page()
    pg.evaluate("plan.tasks.push({id:'m1',title:'Rent',date:'%s',time:'',dur:0,goal:'',repeat:'monthly',days:[],until:'',color:'#fff',tags:[],subs:[],done:{},sdone:{}})" % iso(TODAY.replace(day=15)))
    ok = pg.evaluate("[0,1,2,3].every(i=>{const d=new Date(%d,%d+i,15);return occurs(plan.tasks.at(-1),key(d))})" % (TODAY.year, TODAY.month - 1))
    need(ok, 'not on the 15th'); need(not pg.evaluate("occurs(plan.tasks.at(-1),'%s')" % iso(TODAY.replace(day=16))), 'occurs on the 16th')

@req('PLN-05', 'Subtasks can be added and ticked independently of the parent task.')
def _(E):
    pg = E.page(); nav(pg, 'Planner')
    need(pg.locator('.task .sr').count() == 1, 'seeded subtask not shown')
    pg.click('.task .sr .mchk'); pg.wait_for_timeout(250)
    need(pg.locator('.task .sr.done').count() == 1, 'subtask not ticked')
    need('s1' in data(pg)['plan']['tasks'][1]['sdone'], 'not persisted')

@req('PLN-06', 'Goals: add a goal with start and target dates; link a task to it; the Goals tab lists it with a year timeline.')
def _(E):
    pg = E.page(); nav(pg, 'Planner'); tab(pg, '#ptabs', 'goals')
    need('Half marathon' in pg.inner_text('#pBody'), 'seeded goal missing')
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#glT', 'Learn Spanish'); pg.click('#glOk'); pg.wait_for_timeout(300)
    need('Learn Spanish' in pg.inner_text('#pBody'), 'new goal missing')
    eq(len(data(pg)['plan']['goals']), 2)
    need(pg.locator('#pBody svg, #pBody .tl, #pBody .gl').count() >= 1, 'no timeline visuals')
    nav(pg, 'Planner'); tab(pg, '#ptabs', 'day'); pg.click('.task .info >> nth=0'); pg.wait_for_timeout(250)
    need('Half marathon' in pg.evaluate("[...document.querySelectorAll('#tkG option')].map(o=>o.textContent).join()"), 'goal not selectable')

@req('PLN-07', 'Filter and sort: show all / hide recurring / recurring only, tag chips, and several sort orders.')
def _(E):
    pg = E.page(); nav(pg, 'Planner'); tab(pg, '#ptabs', 'rolling')
    base = pg.locator('.dc .bub, .dc .task, .dc [class*=bub]').count()
    pg.click('#pfBtn'); pg.click('#pfPop button:text-is("Hide recurring")'); pg.wait_for_timeout(250)
    hid = pg.evaluate("pRec"); eq(hid, 'hide')
    pg.click('#pfPop button:text-is("Recurring only")'); pg.wait_for_timeout(250); eq(pg.evaluate("pRec"), 'only')
    pg.click('#pfPop button:text-is("Show all")'); pg.mouse.click(5, 400)
    tags = pg.locator('#pchips .chip').all_inner_texts()
    need('All' in tags and len(tags) >= 3, 'tag chips: %s' % tags)
    pg.click('#poBtn'); need(pg.locator('#poPop button').count() >= 3, 'few sort options')

@req('PLN-08', 'Week tab shows a fixed week from a chosen start day (default Monday) and the choice is remembered.')
def _(E):
    pg = E.page(1280, 860); nav(pg, 'Planner'); tab(pg, '#ptabs', 'week')
    eq(pg.input_value('#wsSel'), '0')
    eq(pg.locator('.dh span').first.inner_text(), 'M')
    pg.select_option('#wsSel', '6'); pg.wait_for_timeout(250)
    eq(pg.locator('.dh span').first.inner_text(), 'S')
    eq(data(pg)['settings']['ws'], 6)

@req('PLN-09', 'Rolling view starts with today as the left-most day and loads further weeks when scrolling sideways.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Planner'); tab(pg, '#ptabs', 'rolling')
    idx = pg.evaluate("[...document.querySelectorAll('.dh')].findIndex(e=>e.classList.contains('today'))")
    need(idx in (0, 7), 'today index %s' % idx)
    need(pg.evaluate("!!document.querySelector('.tgs')"), 'no scroller')
    n = pg.locator('.dh').count(); need(n >= 14, 'only %d days rendered' % n)

@req('PLN-10', 'Weekdays and weekends have two different dark shades on every planner view (day strip, rolling, week) with a repeating 5+2 pattern.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Planner')
    for t in ['rolling', 'week']:
        tab(pg, '#ptabs', t)
        seq = pg.evaluate("[...document.querySelectorAll('.dc')].map(e=>/wb/.test(e.className)?'E':'D').join('')")
        need('EEE' not in seq and 'DDDDDEE' in seq or t == 'week', '%s pattern %s' % (t, seq))
        cols = pg.evaluate("[...new Set([...document.querySelectorAll('.dc')].map(e=>getComputedStyle(e).backgroundColor))]")
        eq(len(cols), 2, t + ' shades')
        for c in cols: need(lum(rgb(c)) < .03, 'shade not dark: ' + c)
    tab(pg, '#ptabs', 'day')
    strip = pg.evaluate("[...document.querySelectorAll('.sd')].slice(0,7).map(e=>[e.className.includes('wb'),getComputedStyle(e).backgroundColor,e.classList.contains('on')])")
    need(len({s[1] for s in strip if s[0] and not s[2]}) <= 1 and len({s[1] for s in strip if not s[0] and not s[2]}) <= 1, 'strip shades inconsistent')

@req('PLN-11', 'Timed tasks appear in the week/rolling grid at their hour as coloured bubbles.')
def _(E):
    pg = E.page(1280, 860); nav(pg, 'Planner'); tab(pg, '#ptabs', 'rolling')
    r = pg.evaluate("""(()=>{const b=[...document.querySelectorAll('.dc *')].find(e=>/Deep work/.test(e.textContent)&&e.children.length<4&&getComputedStyle(e).position==='absolute');
      if(!b)return null;const c=b.closest('.dc').getBoundingClientRect(),r=b.getBoundingClientRect();return {top:r.top-c.top,h:r.height,tot:c.height}})()""")
    need(r, 'no bubble found'); need(r['h'] > 20, 'bubble too small')
    need(abs(r['top'] / r['tot'] - 10 / 24) < .03, 'bubble not at 10:00: %s' % r)

@req('PLN-12', 'Planner statistics tab renders completion figures.')
def _(E):
    pg = E.page(); nav(pg, 'Planner'); tab(pg, '#ptabs', 'stats')
    need(pg.locator('#pBody .tile').count() >= 3, 'no stat tiles')

@req('PLN-13', 'Tags in the planner: tag chips filter the calendar, and the tag field offers suggestions from all pages.')
def _(E):
    pg = E.page(); nav(pg, 'Planner')
    pg.locator('#pchips .chip', has_text='work').click(); pg.wait_for_timeout(250)
    names = pg.locator('.task .name').all_inner_texts()
    need(names == ['Deep work'], 'filter result: %s' % names)
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#tkTg', 'he'); pg.wait_for_timeout(150)
    need('health' in pg.inner_text('#tkTs'), 'no suggestion')

# ============================== BUD ==============================
@req('BUD-01', 'Budget layout: summary tiles above the period tabs; tabs are Week, Month, Year (default Month).')
def _(E):
    pg = E.page(); nav(pg, 'Budget')
    eq(pg.locator('#btabs button').all_inner_texts(), ['Week', 'Month', 'Year'])
    eq(pg.locator('#btabs button.on').inner_text(), 'Month')
    need(pg.evaluate("document.querySelector('#bSum').getBoundingClientRect().top<document.querySelector('#btabs').getBoundingClientRect().top"), 'summary not above tabs')
    eq(pg.locator('#bSum .tile').count(), 4)

@req('BUD-02', 'Each period has its own visualisation (week, month, year charts differ) and the summary figures follow the period.')
def _(E):
    pg = E.page(); nav(pg, 'Budget'); shapes = {}; sums = {}
    for t in ['week', 'month', 'year']:
        tab(pg, '#btabs', t)
        shapes[t] = pg.evaluate("document.querySelector('#bBody').innerHTML.length")
        sums[t] = pg.inner_text('#bSum')
        need(pg.locator('#bBody svg, #bBody .gx, #bBody [class*=chart]').count() >= 1, t + ' has no chart')
    need(len(set(shapes.values())) == 3, 'charts identical')
    need(len(set(sums.values())) == 3, 'summaries identical: %s' % sums)

@req('BUD-03', 'Summary maths: income, expense, savings and left are correct for a known set of entries.')
def _(E):
    d = dict(seed_data()); d['budget'] = []; d['plans'] = []
    pg = E.page(seed=d); nav(pg, 'Budget')
    add_entry(pg, 1000, kind='income'); add_entry(pg, 100, cat='Groceries'); add_entry(pg, 50, kind='saving')
    t = pg.evaluate("[...document.querySelectorAll('#bSum .tile')].map(e=>e.innerText.replace(/\\n/g,' '))")
    joined = ' | '.join(t)
    need('1,000' in joined and '100' in joined and '50' in joined and '850' in joined, 'tiles: ' + joined)

@req('BUD-04', 'Summary tiles are not rebuilt or animated when a filter / same tab is chosen, never animate on period change, and do update when an entry is added.')
def _(E):
    pg = E.page(); nav(pg, 'Budget'); pg.wait_for_timeout(900)
    pg.evaluate("window.__t=document.querySelector('#bSum .tile')")
    for t in ['month', 'month']: tab(pg, '#btabs', t)
    pg.click('#bfBtn'); pg.click('#bfPop button:text-is("Tag")'); pg.mouse.click(5, 400); pg.wait_for_timeout(200)
    need(pg.evaluate("window.__t===document.querySelector('#bSum .tile')"), 'tiles rebuilt although nothing they show changed')
    for t in ['week', 'year', 'month']:
        tab(pg, '#btabs', t)
        need(pg.evaluate("[...document.querySelectorAll('#bSum .tile')].every(e=>e.getAnimations().length===0)"), 'tiles animating on ' + t)
    before = pg.inner_text('#bSum'); add_entry(pg, 77, cat='Groceries')
    need(pg.inner_text('#bSum') != before, 'summary not updated')

@req('BUD-05', 'Entries: amount, category with colour, note, tags, date; the entry shows in the list and the header shows "Spent £x this month".')
def _(E):
    d = dict(seed_data()); d['budget'] = []
    pg = E.page(seed=d); nav(pg, 'Budget')
    add_entry(pg, 12.5, cat='Dining', note='Lunch', tags='work')
    need('Lunch' in pg.inner_text('#bBody') or 'Dining' in pg.inner_text('#bBody'), 'entry not listed')
    need('12.50' in pg.inner_text('#sub'), 'subtitle: ' + pg.inner_text('#sub'))
    e = data(pg)['budget'][0]; eq((e['cat'], e['tags'], e['cur'], e['rate']), ('dining', ['work'], 'GBP', 1))

@req('BUD-06', 'Generic categories with distinct colours include Rent, Salary, Savings, Investments, Groceries, Bills, Transport etc., grouped into income / savings / expense.')
def _(E):
    pg = E.page()
    cats = pg.evaluate("CATS.map(c=>[c.id,c.n,c.k,c.c])")
    names = [c[1] for c in cats]
    for n in ['Rent', 'Salary', 'Savings', 'Investments', 'Groceries', 'Transport', 'Bills & utilities', 'Subscriptions', 'Loan repayment']:
        need(n in names, 'missing category ' + n)
    kinds = {c[2] for c in cats}; eq(kinds, {'income', 'saving', 'expense'})
    eq(len({c[3] for c in cats}), len(cats), 'colours not unique')
    nav(pg, 'Budget'); pg.click('#addBtn'); pg.wait_for_timeout(250)
    need(pg.locator('#txCats .cp', has_text='Rent').count() == 1, 'Rent not offered for expenses')

@req('BUD-07', 'Default currency is GBP; other currencies (incl. AED) are converted using the live rate, and the rate used is stored with the entry.')
def _(E):
    d = dict(seed_data()); d['budget'] = []
    pg = E.page(seed=d, fx='ok'); nav(pg, 'Budget'); pg.wait_for_timeout(500)
    pg.click('#addBtn'); pg.wait_for_timeout(250)
    eq(pg.input_value('#txC'), 'GBP')
    opts = pg.evaluate("[...document.querySelectorAll('#txC option')].map(o=>o.value)"); need('AED' in opts, 'AED missing')
    pg.fill('#txA', '100'); pg.select_option('#txC', 'AED'); pg.wait_for_timeout(300)
    r = float(pg.input_value('#txRt')); need(abs(r - 1 / 4.77) < .001, 'rate %s' % r)
    pg.click('#txOk'); pg.wait_for_timeout(300)
    e = data(pg)['budget'][0]; eq(e['cur'], 'AED'); need(abs(e['rate'] - 1 / 4.77) < .001, 'stored rate %s' % e['rate'])
    need('20.96' in pg.inner_text('#sub'), 'GBP total not shown: ' + pg.inner_text('#sub'))

@req('BUD-08', 'Repeat options: Once, Weekly, Selected days, Every 4 weeks, Monthly, Yearly (+ Until date).')
def _(E):
    pg = E.page(); nav(pg, 'Budget'); pg.click('#addBtn'); pg.wait_for_timeout(250)
    eq(pg.evaluate("[...document.querySelectorAll('#txRp option')].map(o=>o.textContent)"),
       ['Once', 'Weekly', 'Selected days', 'Every 4 weeks', 'Monthly (same date each month)', 'Yearly'])
    pg.select_option('#txRp', 'weekly'); need(pg.is_visible('#txU'), 'until field hidden')

@req('BUD-09', 'Selected days: choose any combination of weekdays (e.g. Tue + Thu); occurrences fall only on those days, starting from the entry date.')
def _(E):
    d = dict(seed_data()); d['budget'] = []; d['plans'] = []
    pg = E.page(seed=d); nav(pg, 'Budget')
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#txA', '5'); pg.select_option('#txRp', 'days'); pg.wait_for_timeout(150)
    eq(pg.locator('#txDays button').count(), 7)
    on = pg.evaluate("[...document.querySelectorAll('#txDays button.on')].map(b=>b.textContent)")
    eq(on, [['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][TODAY.weekday()]], 'default day')
    for x in on: pg.click('#txDays button:text-is("%s")' % x)
    pg.click('#txDays button:text-is("Tue")'); pg.click('#txDays button:text-is("Thu")'); pg.click('#txOk'); pg.wait_for_timeout(300)
    e = data(pg)['budget'][0]; eq((e['repeat'], e['days']), ('days', [1, 3]))
    got = pg.evaluate("occDates(bud[0],'%s','%s')" % (iso(TODAY), iso(TODAY + dt.timedelta(27))))
    want = [iso(TODAY + dt.timedelta(i)) for i in range(28) if (TODAY + dt.timedelta(i)).weekday() in (1, 3)]
    eq(got, want)
    need('Tue, Thu' in pg.inner_text('#bBody'), 'label not shown')

@req('BUD-10', 'Selected days with nothing chosen is refused; edits keep the chosen days.')
def _(E):
    pg = E.page(seed=False); nav(pg, 'Budget')
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#txA', '5'); pg.select_option('#txRp', 'days'); pg.wait_for_timeout(100)
    for x in pg.evaluate("[...document.querySelectorAll('#txDays button.on')].map(b=>b.textContent)"): pg.click('#txDays button:text-is("%s")' % x)
    pg.click('#txOk'); pg.wait_for_timeout(250)
    need(pg.locator('#txM.open').count() == 1 and not data(pg)['budget'], 'saved without any day')

@req('BUD-11', 'Recurrence rules: weekly = every 7 days, every 4 weeks = 28 days, monthly keeps the date (clamped to month end), yearly keeps the date; "until" stops it.')
def _(E):
    pg = E.page()
    r = pg.evaluate("""(()=>{const mk=(rep,d,u)=>({date:d,repeat:rep,until:u||'',days:[]});
      return {w:occDates(mk('weekly','2026-01-05'),'2026-01-01','2026-02-01'),f:occDates(mk('fourweekly','2026-01-05'),'2026-01-01','2026-03-31'),
      m:occDates(mk('monthly','2026-01-31'),'2026-01-01','2026-04-30'),y:occDates(mk('yearly','2024-02-29'),'2024-01-01','2026-12-31'),u:occDates(mk('weekly','2026-01-05','2026-01-20'),'2026-01-01','2026-12-31')}})()""")
    eq(r['w'], ['2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26'])
    eq(r['f'], ['2026-01-05', '2026-02-02', '2026-03-02', '2026-03-30'])
    eq(r['m'], ['2026-01-31', '2026-02-28', '2026-03-31', '2026-04-30'])
    eq(r['y'], ['2024-02-29', '2025-02-28', '2026-02-28'])
    eq(r['u'], ['2026-01-05', '2026-01-12', '2026-01-19'])

@req('BUD-12', 'Payment plan: full amount, APR, monthly payment and day; the schedule is generated until paid off; maths matches the standard amortisation formula.')
def _(E):
    pg = E.page(); nav(pg, 'Budget'); pg.click('#addBtn'); pg.wait_for_timeout(250)
    eq(pg.locator('#txK button').all_inner_texts(), ['Expense', 'Income', 'Savings', 'Payment plan'])
    pg.click('#txK [data-k=plan]'); pg.wait_for_timeout(450)
    need(pg.locator('#plM.open').count() == 1 and pg.locator('#txM.open').count() == 0, 'plan sheet did not replace entry sheet')
    pg.fill('#plN', 'Phone'); pg.fill('#plA', '1200'); pg.fill('#plR', '12'); pg.fill('#plP', '200'); pg.click('#plOk'); pg.wait_for_timeout(400)
    p = data(pg)['plans'][-1]; eq((p['name'], p['principal'], p['apr'], p['pay']), ('Phone', 1200, 12, 200))
    rows = pg.evaluate("planRows(bplans.at(-1))")
    bal = 1200.0; n = 0; interest = 0.0
    while bal > .005 and n < 100:
        i = bal * .01; interest += i; bal = bal + i - 200; n += 1
    eq(len(rows), n, 'number of payments'); need(abs(sum(r['int'] for r in rows) - interest) < .05, 'interest total')
    need(abs(rows[-1]['bal']) < .01, 'last balance not zero')

@req('BUD-13', 'Extra (early) payments can be added to a plan and shorten it.')
def _(E):
    pg = E.page()
    base = pg.evaluate("planRows(bplans[0]).length")
    pg.evaluate("bplans[0].extras=[{date:'%s',amt:500}]" % iso(TODAY))
    short = pg.evaluate("planRows(bplans[0]).length")
    need(short < base, 'not shorter (%s vs %s)' % (short, base))
    nav(pg, 'Budget'); pg.locator('.sbtn').first.click(); pg.wait_for_timeout(450)
    need(pg.locator('#plM.open').count() == 1 and pg.locator('#plXa').is_visible(), 'no extra payment button')

@req('BUD-14', 'Payment plans appear under "Recurring and payment plans" with progress and next payment.')
def _(E):
    pg = E.page(); nav(pg, 'Budget')
    txt = pg.inner_text('#bBody')
    need('Car loan' in txt and 'Recurring' in txt, 'plan not listed')

@req('BUD-15', 'Filter popover: Show (all/spent/income/saved), Include (all/recurring/one-off), Break down by (category/tag); each changes the numbers shown.')
def _(E):
    pg = E.page(); nav(pg, 'Budget'); pg.click('#bfBtn'); pg.wait_for_timeout(300)
    txt = pg.inner_text('#bfPop').lower()
    for w in ['show', 'include', 'break down by']: need(w in txt, w + ' missing')
    a = pg.inner_text('#bBody')
    pg.click('#bfPop button:text-is("Recurring only")'); pg.wait_for_timeout(250); b = pg.inner_text('#bBody'); need(a != b, 'include had no effect')
    pg.click('#bfPop button:text-is("Tag")'); pg.wait_for_timeout(250); c = pg.inner_text('#bBody'); need(b != c, 'break down had no effect')
    pg.click('#bfPop button:text-is("Income")'); pg.wait_for_timeout(250)

@req('BUD-16', 'Breakdown shows every category / tag with its total amount and percentage of the whole.')
def _(E):
    pg = E.page(); nav(pg, 'Budget'); tab(pg, '#btabs', 'year')
    rows = pg.evaluate("[...document.querySelectorAll('#bBody .cb, #bBody [class*=brk] li, #bBody .cr')].map(e=>e.innerText.replace(/\\n/g,' '))")
    need(rows, 'no breakdown rows found')
    need(all('%' in r and re.search(r'[£\d]', r) for r in rows), 'rows missing percent or amount: ' + str(rows[:2]))

@req('BUD-17', 'Tags on budget entries: chips filter the entries; the tag field suggests tags used anywhere in the app.')
def _(E):
    pg = E.page(); nav(pg, 'Budget')
    chips = pg.locator('#bchips .chip').all_inner_texts(); need(len(chips) >= 3, 'chips: %s' % chips)
    pg.locator('#bchips .chip', has_text='home').click(); pg.wait_for_timeout(250)
    need(pg.evaluate("bTag") == 'home', 'filter not applied')
    pg.locator('#bchips .chip').first.click()
    pg.click('#addBtn'); pg.wait_for_timeout(250); pg.fill('#txTg', 'he'); pg.wait_for_timeout(150)
    need('health' in pg.inner_text('#txTs'), 'habit tag not suggested in budget')

@req('BUD-18', 'Budget export button (CSV) is on the budget page.')
def _(E):
    pg = E.page(); nav(pg, 'Budget')
    with pg.expect_download() as dl: pg.click('#bExp')
    need(dl.value.suggested_filename.startswith('budget-') and dl.value.suggested_filename.endswith('.csv'), dl.value.suggested_filename)

# ============================== JRN ==============================
HRS = "(()=>[...document.querySelectorAll('.hgrid .hc')])()"

@req('JRN-01', 'Journal entry: day navigation, five mood buttons, grateful-for, notes; saved automatically; word count and entries list update.')
def _(E):
    pg = E.page(seed=False); nav(pg, 'Journal')
    eq(pg.locator('.mood button').all_inner_texts(), ['Rough', 'Low', 'Okay', 'Good', 'Great'])
    pg.click('.mood button:text-is("Good")'); pg.fill('#jg', 'Coffee'); pg.fill('#jt', 'One two three four'); pg.wait_for_timeout(700)
    e = data(pg)['journal'][iso(TODAY)]; eq((e['m'], e['g'], e['t']), (4, 'Coffee', 'One two three four'))
    need('4 words' in pg.inner_text('#jc'), pg.inner_text('#jc'))
    need('Good' in pg.inner_text('#jEnt'), 'entries list not updated')
    eq(pg.inner_text('#sub'), 'Written today')
    pg.click('.nav button >> nth=0'); pg.wait_for_timeout(300); eq(pg.input_value('#jt'), '')

@req('JRN-02', 'Journal search filters the entries list; tiles show entries, streak, words and average mood.')
def _(E):
    j = {iso(TODAY): dict(m=5, g='', t='alpha beta'), iso(TODAY - dt.timedelta(1)): dict(m=3, g='', t='gamma delta epsilon'), iso(TODAY - dt.timedelta(5)): dict(m=1, g='', t='zeta')}
    d = seed_data(); d['journal'] = j
    pg = E.page(seed=d); nav(pg, 'Journal')
    tiles = pg.evaluate("[...document.querySelectorAll('.tile')].map(e=>e.innerText.replace(/\\n/g,' '))")
    need(tiles[0].startswith('3') and tiles[1].startswith('2d') and tiles[2].startswith('6'), 'tiles: %s' % tiles)
    pg.fill('#js', 'gamma'); pg.wait_for_timeout(200); eq(pg.locator('#jEnt .en').count(), 1)

@req('JRN-03', 'Hourly mood is a single scrollable row of 24 hour slots; today\'s current hour is the second-from-last visible slot; future hours are disabled.')
def _(E):
    for w in [390, 1280]:
        pg = E.page(w, 860); nav(pg, 'Journal'); pg.wait_for_timeout(400)
        eq(pg.locator('.hgrid .hc').count(), 24)
        r = pg.evaluate("""(()=>{const g=document.querySelector('.hgrid'),gr=g.getBoundingClientRect(),cs=[...g.querySelectorAll('.hc')];
          const vis=cs.filter(c=>{const r=c.getBoundingClientRect();return r.left>=gr.left-2&&r.right<=gr.right+2});
          return {rows:new Set(cs.map(c=>Math.round(c.getBoundingClientRect().top))).size,now:vis.indexOf(g.querySelector('.hc.now')),n:vis.length,dis:cs.filter(c=>c.disabled).length}})()""")
        eq(r['rows'], 1, 'rows at %d' % w)
        h = NOW.hour
        if h < 23:
            eq(r['now'], r['n'] - 2, 'current hour position at %d: %s' % (w, r))
        eq(r['dis'], 23 - h, 'future hours disabled')

@req('JRN-04', 'Arrow buttons beside the hour row scroll it; they disable at the ends.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Journal'); pg.wait_for_timeout(400)
    s0 = pg.evaluate("document.querySelector('.hgrid').scrollLeft")
    pg.click('.hrow > button >> nth=0'); pg.wait_for_timeout(600)
    need(pg.evaluate("document.querySelector('.hgrid').scrollLeft") < s0, 'did not scroll back')
    pg.click('.hrow > button >> nth=1'); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('.hgrid').style.scrollBehavior='auto';document.querySelector('.hgrid').scrollLeft=0")
    pg.wait_for_timeout(500)
    need(pg.evaluate("document.querySelector('.hrow > button').disabled"), 'left arrow not disabled at start')

def _open_hour(pg, h):
    pg.locator('.hgrid .hc').nth(h).scroll_into_view_if_needed()
    pg.locator('.hgrid .hc').nth(h).click(); pg.wait_for_timeout(350)

@req('JRN-05', 'Emotion wheel: 6 core emotions in the centre ring, 18 specific emotions in the outer ring, plus 2 refinements shown as chips once one is chosen.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Journal'); _open_hour(pg, 0)
    need(pg.locator('#emM.open').count() == 1, 'sheet not open')
    eq(pg.locator('.ew path[data-c]:not([data-s])').count(), 6)
    eq(pg.locator('.ew path[data-s]').count(), 18)
    pg.locator('.ew path[data-c="Joyful"]:not([data-s])').click(); pg.locator('.ew path[data-s="Proud"]').click(); pg.wait_for_timeout(150)
    eq(pg.locator('#emChips .cp').all_inner_texts(), ['Confident', 'Successful'])
    pg.locator('#emChips .cp >> nth=0').click(); pg.wait_for_timeout(100)
    eq(pg.inner_text('#emPath'), 'Joyful › Proud › Confident')

@req('JRN-06', 'Saving an hour stores core/secondary/tertiary/note under that date and hour; the slot shows its colour and emotion name.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Journal'); _open_hour(pg, 0)
    pg.locator('.ew path[data-s="Anxious"]').click(); pg.fill('#emNote', 'Big day'); pg.click('#emOk'); pg.wait_for_timeout(400)
    h = data(pg)['journal'][iso(TODAY)]['h']['0']; eq((h['core'], h['sec'], h['note']), ('Scared', 'Anxious', 'Big day'))
    cell = pg.locator('.hgrid .hc').nth(0); need('Anxious' in cell.inner_text(), 'name not on slot')
    need('f' in (cell.get_attribute('class') or '').split(), 'slot not marked filled')

@req('JRN-07', 'Clear removes an hour; a day with nothing left is removed from storage.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Journal'); _open_hour(pg, 0)
    pg.locator('.ew path[data-c="Sad"]:not([data-s])').click(); pg.click('#emOk'); pg.wait_for_timeout(300)
    _open_hour(pg, 0); pg.click('#emClear'); pg.wait_for_timeout(300)
    need(iso(TODAY) not in data(pg)['journal'], 'empty day kept')

@req('JRN-08', 'Previous/next hour arrows inside the wheel sheet auto-save the chosen emotion and move on; Next is disabled beyond the current hour today.')
def _(E):
    d = seed_data(); y = iso(TODAY - dt.timedelta(1))
    pg = E.page(seed=d); nav(pg, 'Journal'); pg.click('.nav button >> nth=0'); pg.wait_for_timeout(350)
    _open_hour(pg, 12)
    pg.locator('.ew path[data-c="Mad"]:not([data-s])').click(); pg.click('#emNext'); pg.wait_for_timeout(250)
    need('1 PM' in pg.inner_text('#emH') or '13' in pg.inner_text('#emH'), pg.inner_text('#emH'))
    need(pg.inner_text('#emPath').startswith('Tap'), 'new hour not blank')
    need(data(pg)['journal'][y]['h']['12']['core'] == 'Mad', 'previous hour not auto-saved')
    pg.click('#emCancel'); pg.wait_for_timeout(300)
    pg2 = E.page(390, 844); nav(pg2, 'Journal'); _open_hour(pg2, NOW.hour)
    need(pg2.evaluate("document.querySelector('#emNext').disabled"), 'next not disabled at current hour')

@req('JRN-09', 'Mood curve: a chart with one dot per logged hour, a legend of the emotions used and a one-line summary (check-ins, average feeling, most frequent).')
def _(E):
    y = iso(TODAY - dt.timedelta(1)); d = seed_data()
    d['journal'] = {y: dict(h={'8': dict(core='Joyful', sec='', ter='', note=''), '12': dict(core='Sad', sec='Lonely', ter='', note=''), '18': dict(core='Joyful', sec='Proud', ter='', note='')})}
    pg = E.page(seed=d); nav(pg, 'Journal'); pg.click('.nav button >> nth=0'); pg.wait_for_timeout(350)
    eq(pg.locator('svg.mcv circle').count(), 3)
    txt = pg.inner_text('#jBody .panel >> nth=0')
    need('3 check-ins' in txt and 'average feeling' in txt and 'most often' in txt, txt[-120:])
    need('Joyful' in txt and 'Sad' in txt, 'legend missing')
    need(pg.locator('svg.mcv title').count() >= 3, 'no hover titles')

@req('JRN-10', 'Wheel accessibility: segments are focusable buttons with labels, selectable with Enter/Space; text on every segment has readable contrast.')
def _(E):
    pg = E.page(390, 844); nav(pg, 'Journal'); _open_hour(pg, 0)
    need(pg.evaluate("[...document.querySelectorAll('.ew path')].every(p=>p.getAttribute('tabindex')==='0'&&p.getAttribute('role')==='button'&&p.getAttribute('aria-label'))"), 'segments not accessible')
    pg.focus('.ew path[data-c="Peaceful"]:not([data-s])'); pg.keyboard.press('Enter'); pg.wait_for_timeout(150)
    need(pg.inner_text('#emPath').startswith('Peaceful'), 'Enter did not select')
    pairs = pg.evaluate("""(()=>{const out=[];document.querySelectorAll('.ew path').forEach(p=>{const t=p.getAttribute('aria-label').split(', ').pop();const tx=[...document.querySelectorAll('.ew text')].find(x=>x.textContent===t);if(tx)out.push([t,getComputedStyle(p).fill,tx.getAttribute('fill')])});return out})()""")
    need(len(pairs) >= 24, 'too few labelled segments: %d' % len(pairs))
    hexrgb = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)] if len(h) == 7 else [int(ch * 2, 16) for ch in h[1:]]
    bad = [(n, round(contrast(rgb(f), hexrgb(c) if c.startswith('#') else rgb(c)), 1)) for n, f, c in pairs if contrast(rgb(f), hexrgb(c) if c.startswith('#') else rgb(c)) < 4.5]
    need(not bad, 'low contrast labels: %s' % bad[:4])

@req('JRN-11', 'Hourly moods are included in the export, show in the entries list ("n mood check-ins") and count as a journal entry.')
def _(E):
    y = iso(TODAY - dt.timedelta(1)); d = seed_data(); d['journal'] = {y: dict(h={'9': dict(core='Peaceful', sec='', ter='', note='')})}
    pg = E.page(seed=d); nav(pg, 'Journal')
    need('1 mood check-ins' in pg.inner_text('#jEnt'), pg.inner_text('#jEnt')[:80])
    pg.click('#dataBtn'); pg.wait_for_timeout(250)
    with pg.expect_download() as dl: pg.click('#expBtn')
    j = json.loads(Path(dl.value.path()).read_text(encoding='utf-8'))
    eq(j['journal'][y]['h']['9']['core'], 'Peaceful')
    need(pg.evaluate("hasE(jr['%s'])" % y), 'not counted as entry')


def _body_seed(weights=None, kcal=None):
    d = seed_data(); j = {}
    for off, kg in (weights or {}).items():
        j.setdefault(iso(TODAY - dt.timedelta(off)), {})['w'] = kg
    for off, items in (kcal or {}).items():
        j.setdefault(iso(TODAY - dt.timedelta(off)), {})['f'] = [dict(m=m, k=k, n=n) for m, k, n in items]
    d['journal'] = j
    return d

@req('JRN-12', 'Weight: enter today\'s weight (decimals allowed); it is saved automatically in kg under the date, shows the change since the previous logged weight, and counts as a journal entry.')
def _(E):
    pg = E.page(seed=_body_seed({3: 80.0})); nav(pg, 'Journal')
    pg.fill('#wIn', '79.4'); pg.wait_for_timeout(700)
    eq(data(pg)['journal'][iso(TODAY)]['w'], 79.4)
    need('0.6 kg since' in pg.inner_text('#wMeta').replace('\u2212', '-').replace('-', '') or '0.6' in pg.inner_text('#wMeta'), pg.inner_text('#wMeta'))
    need('\u2212' in pg.inner_text('#wMeta'), 'loss not shown with a minus: ' + pg.inner_text('#wMeta'))
    eq(pg.inner_text('#sub'), 'Written today')
    pg.fill('#wIn', ''); pg.wait_for_timeout(700)
    need(iso(TODAY) not in data(pg)['journal'], 'empty weight kept the day')

@req('JRN-13', 'Weight unit kg / lb: switching converts what is shown, storage stays in kg, and the choice is remembered (also in the exported settings).')
def _(E):
    pg = E.page(seed=_body_seed({0: 80.0})); nav(pg, 'Journal')
    eq(pg.input_value('#wIn'), '80')
    pg.click('#wUnit [data-u=lb]'); pg.wait_for_timeout(300)
    need(abs(float(pg.input_value('#wIn')) - 176.4) < .11, pg.input_value('#wIn'))
    eq(pg.inner_text('#wU'), 'lb')
    eq(data(pg)['journal'][iso(TODAY)]['w'], 80.0)
    eq(data(pg)['settings']['wu'], 'lb')
    pg.fill('#wIn', '176.4'); pg.wait_for_timeout(700)
    need(abs(data(pg)['journal'][iso(TODAY)]['w'] - 80.01) < .05, 'stored value not kg: %s' % data(pg)['journal'][iso(TODAY)]['w'])
    pg.reload(); pg.wait_for_timeout(500); nav(pg, 'Journal'); eq(pg.inner_text('#wU'), 'lb')

@req('JRN-14', 'Weight trend chart: one dot per logged day with a line between them, axis labels and hover values; 30 / 90 day switch changes the window.')
def _(E):
    w = {i: 80 - i * .05 for i in range(0, 80, 4)}
    pg = E.page(seed=_body_seed(w)); nav(pg, 'Journal')
    n30 = pg.locator('#wViz svg circle').count(); need(n30 == len([i for i in w if i < 30]), 'dots for 30 days: %d' % n30)
    need(pg.locator('#wViz svg polyline').count() == 1 and pg.locator('#wViz svg title').count() == n30, 'line / tooltips missing')
    pg.click('#wRng [data-r="90"]'); pg.wait_for_timeout(250)
    n90 = pg.locator('#wViz svg circle').count(); need(n90 == len(w) and n90 > n30, 'dots for 90 days: %d' % n90)
    pg.reload(); pg.wait_for_timeout(450); nav(pg, 'Journal')
    need(pg.locator('#wRng button.on').inner_text().startswith('90'), 'range not remembered')
    pg2 = E.page(seed=_body_seed()); nav(pg2, 'Journal')
    need(pg2.locator('#wViz svg').count() == 0 and 'Log your weight' in pg2.inner_text('#wMeta'), 'empty state')

@req('JRN-15', 'Calories: choose a meal (Breakfast / Lunch / Dinner / Snack), enter kcal and an optional description, Add; the total, remaining amount and progress bar update; entries can be removed; invalid amounts are refused.')
def _(E):
    pg = E.page(seed=_body_seed()); nav(pg, 'Journal')
    eq(pg.locator('#cMeals button').all_inner_texts(), ['Breakfast', 'Lunch', 'Dinner', 'Snack'])
    pg.click('#cMeals button:text-is("Lunch")'); pg.fill('#cK', '650'); pg.fill('#cN', 'Pasta'); pg.click('#cAdd'); pg.wait_for_timeout(250)
    pg.click('#cMeals button:text-is("Snack")'); pg.fill('#cK', '150'); pg.keyboard.press('Enter'); pg.wait_for_timeout(250)
    f = data(pg)['journal'][iso(TODAY)]['f']; eq([(x['m'], x['k'], x['n']) for x in f], [('l', 650, 'Pasta'), ('s', 150, '')])
    eq(pg.inner_text('#cT2'), '800'); need('1,200 kcal left' in pg.inner_text('#cOf'), pg.inner_text('#cOf'))
    need(abs(float(pg.evaluate("parseFloat(document.querySelector('#cB').style.width)")) - 40) < .5, 'bar width')
    eq(pg.locator('#cList .cit').count(), 2)
    pg.fill('#cK', '0'); pg.click('#cAdd'); pg.fill('#cK', ''); pg.click('#cAdd'); pg.wait_for_timeout(200)
    eq(len(data(pg)['journal'][iso(TODAY)]['f']), 2, 'invalid amount saved')
    pg.click('#cList .cit button >> nth=0'); pg.wait_for_timeout(250)
    eq(pg.inner_text('#cT2'), '150'); eq(len(data(pg)['journal'][iso(TODAY)]['f']), 1)
    pg.click('#cList .cit button >> nth=0'); pg.wait_for_timeout(250)
    need(iso(TODAY) not in data(pg)['journal'], 'empty day kept')

@req('JRN-16', 'Calorie goal: default 2,000, editable (500-20,000) and remembered; going over the goal says so and turns the bar and chart bar amber.')
def _(E):
    pg = E.page(seed=_body_seed({0: None} if False else None, {0: [('d', 2300, 'Feast')]})); nav(pg, 'Journal')
    eq(pg.input_value('#cGoal'), '2000'); need('300 kcal over goal of 2,000' in pg.inner_text('#cOf'), pg.inner_text('#cOf'))
    need(pg.evaluate("getComputedStyle(document.querySelector('#cB')).backgroundColor") == 'rgb(245, 158, 11)', 'bar not amber')
    pg.fill('#cGoal', '2500'); pg.press('#cGoal', 'Tab'); pg.wait_for_timeout(250)
    need('200 kcal left of 2,500' in pg.inner_text('#cOf'), pg.inner_text('#cOf'))
    eq(data(pg)['settings']['cg'], 2500)
    pg.fill('#cGoal', '10'); pg.press('#cGoal', 'Tab'); pg.wait_for_timeout(200)
    eq(pg.input_value('#cGoal'), '2500', 'invalid goal accepted')
    pg.reload(); pg.wait_for_timeout(450); nav(pg, 'Journal'); eq(pg.input_value('#cGoal'), '2500')

@req('JRN-17', 'Calories chart: last 14 days as bars against a dashed goal line, with legend (within / over goal), hover values and a 7-day average that matches the data.')
def _(E):
    k = {0: [('b', 500, '')], 1: [('l', 2500, '')], 2: [('d', 1500, '')], 20: [('d', 9999, '')]}
    pg = E.page(seed=_body_seed(None, k)); nav(pg, 'Journal')
    eq(pg.locator('#cViz svg rect').count(), 3, 'bars (day 20 is outside 14 days)')
    need(pg.locator('#cViz svg line[stroke-dasharray]').count() == 1, 'goal line missing')
    need('Within goal' in pg.inner_text('#cLg') and 'Over goal' in pg.inner_text('#cLg'), 'legend')
    need(pg.locator('#cViz svg rect title').count() == 3, 'hover titles')
    need('1,500 kcal on 3 logged days' in pg.inner_text('#cAvg'), pg.inner_text('#cAvg'))

@req('JRN-18', 'Weight and calories appear in the journal entries list, are exported / imported with the data, and count towards the journal streak.')
def _(E):
    pg = E.page(seed=_body_seed({1: 75.5}, {1: [('b', 400, ''), ('l', 600, '')], 2: [('d', 700, '')]})); nav(pg, 'Journal')
    txt = pg.inner_text('#jEnt'); need('75.5 kg' in txt and '1,000 kcal' in txt and '700 kcal' in txt, txt[:200])
    need(pg.evaluate("hasE(jr['%s'])" % iso(TODAY - dt.timedelta(1))), 'not counted as entry')
    pg.click('#dataBtn'); pg.wait_for_timeout(250)
    with pg.expect_download() as dl: pg.click('#expBtn')
    j = json.loads(Path(dl.value.path()).read_text(encoding='utf-8'))
    y = iso(TODAY - dt.timedelta(1)); eq((j['journal'][y]['w'], len(j['journal'][y]['f'])), (75.5, 2)); need('wu' in j['settings'] and 'cg' in j['settings'], 'settings missing')
    pg.evaluate("closeAll()")
    tiles = pg.evaluate("[...document.querySelectorAll('.tile')].map(e=>e.innerText.replace(/\\n/g,' '))"); need(tiles[1].startswith('2d'), 'streak: %s' % tiles)

@req('JRN-19', 'Weight and calories panels fit at 320 px (no sideways scroll), sit side by side on laptops, and their fields use 16 px text so iOS does not zoom.')
def _(E):
    for w in [320, 360]:
        pg = E.page(w, 740, seed=_body_seed({0: 80, 3: 79}, {0: [('b', 400, 'x' * 60)]})); nav(pg, 'Journal')
        need(no_overflow(pg), 'overflow at %d' % w)
        need(pg.evaluate("[...document.querySelectorAll('.bn .panel')].every(p=>p.scrollWidth<=p.clientWidth+1)"), 'panel content clipped at %d' % w)
    pg = E.page(1280, 860, seed=_body_seed({0: 80})); nav(pg, 'Journal')
    tops = pg.evaluate("[...document.querySelectorAll('.bn .panel')].map(p=>Math.round(p.getBoundingClientRect().top))"); need(len(tops) == 2 and max(tops) - min(tops) < 12, 'panels not side by side: %s' % tops)
    fs = pg.evaluate("[...document.querySelectorAll('.bn input')].map(e=>parseFloat(getComputedStyle(e).fontSize)).filter(x=>x<16).length"); eq(fs, 0, 'small input text')

# ============================== PD ==============================
@req('PD-01', 'Clock: shows the current time and date, seconds tick, AM/PM is shown separately, and the date line has no stray separators.')
def _(E):
    pg = E.page(); a = pg.inner_text('#cT'); pg.wait_for_timeout(1300); b = pg.inner_text('#cT')
    need(a != b, 'clock not ticking')
    now = dt.datetime.now(ZoneInfo(TZ))
    hh = pg.evaluate("document.querySelector('#cT').childNodes[0].textContent")
    m = re.match(r'(\d+):(\d+)', hh); need(m, hh)
    shown = (int(m.group(1)) % 12, int(m.group(2))); real = (now.hour % 12, now.minute)
    need(abs((shown[0] * 60 + shown[1]) - (real[0] * 60 + real[1])) % 720 <= 2, 'time off: %s vs %s' % (shown, real))
    need(now.strftime('%A') in pg.inner_text('#cD') and str(now.day) in pg.inner_text('#cD'), pg.inner_text('#cD'))
    need('·' not in pg.inner_text('#cD'), 'stray separator')

@req('PD-02', 'Clock and Pomodoro sit in the same place on every page and are not rebuilt when switching pages.')
def _(E):
    pg = E.page(); pg.evaluate("window.__c=document.querySelector('#cT');window.__p=document.querySelector('#pomo')")
    pos = []
    for p in ['Habits', 'Planner', 'Budget', 'Journal']:
        nav(pg, p); pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(100); pos.append(pg.evaluate("[document.querySelector('#pomo').getBoundingClientRect().top,document.querySelector('#cT').getBoundingClientRect().top]"))
    need(len({tuple(map(round, x)) for x in pos}) == 1, 'positions differ: %s' % pos)
    need(pg.evaluate("window.__c===document.querySelector('#cT')&&window.__p===document.querySelector('#pomo')"), 'header rebuilt')

@req('PD-03', 'Pomodoro: default 25:00 focus / 5:00 break; start counts down, pause holds, reset restores, switching mode sets the other length.')
def _(E):
    pg = E.page(); eq(pg.inner_text('#pt'), '25:00')
    pg.click('#pp'); pg.wait_for_timeout(2300); t = pg.inner_text('#pt'); need(t in ('24:57', '24:58', '24:59'), t)
    pg.click('#pp'); a = pg.inner_text('#pt'); pg.wait_for_timeout(1200); eq(pg.inner_text('#pt'), a, 'paused timer moved')
    pg.click('#pr'); eq(pg.inner_text('#pt'), '25:00')
    pg.click('#pm [data-m=break]'); eq(pg.inner_text('#pt'), '05:00')
    need(pg.evaluate("document.querySelector('#pp svg')!==null"), 'play button not an icon')

@req('PD-04', 'Pomodoro keeps running while switching between pages, and the browser tab title shows the countdown.')
def _(E):
    pg = E.page(); pg.click('#pp'); pg.wait_for_timeout(1200)
    a = pg.evaluate("pm.left")
    for p in ['Planner', 'Budget', 'Journal', 'Habits']: nav(pg, p)
    b = pg.evaluate("pm.left"); need(pg.evaluate("pm.run") and b < a, 'timer stopped: %s -> %s' % (a, b))
    need(re.match(r'\d\d:\d\d · ', pg.title()), 'title: ' + pg.title())

@req('PD-05', 'Pomodoro lengths are adjustable 1 to 60 minutes (never above 60) and are remembered.')
def _(E):
    pg = E.page(); pg.click('#psBtn')
    eq((pg.get_attribute('#fr', 'min'), pg.get_attribute('#fr', 'max'), pg.get_attribute('#br', 'max')), ('1', '60', '60'))
    pg.evaluate("(()=>{const r=document.querySelector('#fr');r.value=999;r.dispatchEvent(new Event('input'))})()")
    eq(pg.inner_text('#pt'), '60:00')
    pg.evaluate("(()=>{const r=document.querySelector('#br');r.value=10;r.dispatchEvent(new Event('input'))})()")
    pg.reload(); pg.wait_for_timeout(450); eq(pg.inner_text('#pt'), '60:00')
    pg.click('#pm [data-m=break]'); eq(pg.inner_text('#pt'), '10:00')

@req('PD-06', 'Completing a focus session beeps (no error), counts "n sessions today" and switches to break.')
def _(E):
    pg = E.page(); pg.evaluate("pm.run=true;pm.end=Date.now()+600"); pg.wait_for_timeout(1500)
    eq(pg.evaluate("pm.mode"), 'break'); need('1 session' in pg.inner_text('#pc'), pg.inner_text('#pc'))
    eq(pg.evaluate("JSON.parse(localStorage.getItem('ht_pomo')).n"), 1)
    need(not pg.errs, str(pg.errs))

@req('PD-07', 'Live exchange rates: three currencies are shown under the timer with an "updated" time when the source answers.')
def _(E):
    pg = E.page(fx='ok', wait=900)
    spans = pg.locator('#fxv span').all_inner_texts(); eq(len(spans), 3)
    txt = pg.inner_text('#fxv'); need('1.30' in txt or '1.300' in txt, txt); need('1.15' in txt, txt)
    need(pg.inner_text('#fxu').startswith('updated'), pg.inner_text('#fxu'))
    eq(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('ht_fx')).r).includes('USD')"), True)

@req('PD-08', 'Exchange rates fall back to the next source if the first fails.')
def _(E):
    pg = E.page(fx='second', wait=900)
    need(pg.inner_text('#fxu').startswith('updated'), pg.inner_text('#fxu'))
    need(any('frankfurter' in u for u in pg.reqs), 'fallback source not used: %s' % pg.reqs)

@req('PD-09', 'When every source fails the row says "offline · tap to retry", keeps the last known rates, and tapping retries.')
def _(E):
    cache = dict(t=int(time.time() * 1000) - 4000000, r=FX_OK['rates'])
    pg = E.page(fx='fail', wait=900, init="localStorage.setItem('ht_fx',%s)" % json.dumps(json.dumps(cache)))
    need('offline' in pg.inner_text('#fxu') and 'retry' in pg.inner_text('#fxu'), pg.inner_text('#fxu'))
    need('1.30' in pg.inner_text('#fxv') or '1.300' in pg.inner_text('#fxv'), 'cached rate not shown')
    n = len(pg.reqs); pg.click('#fxu'); pg.wait_for_timeout(500); need(len(pg.reqs) > n, 'retry made no request')

@req('PD-10', 'Exchange-rate currencies are chosen from three drop-downs (AED included), shown immediately and remembered.')
def _(E):
    pg = E.page(fx='ok', wait=900); pg.click('#fxBtn')
    need('AED' in pg.evaluate("[...document.querySelectorAll('#fx1 option')].map(o=>o.value)"), 'AED not offered')
    pg.select_option('#fx3', 'JPY'); pg.wait_for_timeout(200)
    need('JPY' in pg.inner_text('#fxv') and '195' in pg.inner_text('#fxv'), pg.inner_text('#fxv'))
    pg.reload(); pg.wait_for_timeout(700); need('JPY' in pg.inner_text('#fxv'), 'not remembered')

@req('PD-11', 'AED has a built-in peg (3.6725 per USD) when a source does not list it.')
def _(E):
    pg = E.page(fx='noaed', wait=900); pg.click('#fxBtn'); pg.select_option('#fx1', 'AED'); pg.wait_for_timeout(200)
    v = pg.evaluate("fx.r.AED"); need(abs(v - 1.30 * 3.6725) < .01, 'AED rate %s' % v)

@req('PD-12', 'Header sub-title is live per page: habits done, tasks done, spent this month, journal written.')
def _(E):
    pg = E.page()
    eq(pg.inner_text('#sub'), '2 of 3 done today')   # 'Read' ticked today + quit habit clean today
    nav(pg, 'Planner'); need('tasks done today' in pg.inner_text('#sub'), pg.inner_text('#sub'))
    nav(pg, 'Budget'); need(re.match(r'Spent £[\d,.]+ this month', pg.inner_text('#sub')), pg.inner_text('#sub'))
    nav(pg, 'Journal'); eq(pg.inner_text('#sub'), 'Nothing written today')
    pg.click('.mood button >> nth=2'); pg.wait_for_timeout(300); eq(pg.inner_text('#sub'), 'Written today')

@req('PD-13', 'Spent-this-month in the header equals the sum of this month\'s expense entries (including recurring occurrences).')
def _(E):
    d = seed_data(); d['plans'] = []
    first = TODAY.replace(day=1)
    d['budget'] = [dict(id='a', date=iso(TODAY), cat='groc', amt=40, cur='GBP', rate=1, note='', tags=[], repeat='none', until=''),
                   dict(id='b', date=iso(first), cat='shop', amt=10, cur='GBP', rate=1, note='', tags=[], repeat='none', until=''),
                   dict(id='c', date=iso(first - dt.timedelta(40)), cat='shop', amt=999, cur='GBP', rate=1, note='', tags=[], repeat='none', until=''),
                   dict(id='i', date=iso(TODAY), cat='salary', amt=2000, cur='GBP', rate=1, note='', tags=[], repeat='none', until='')]
    pg = E.page(seed=d); nav(pg, 'Budget')
    eq(pg.inner_text('#sub'), 'Spent £50.00 this month')

@req('PD-14', 'Journal tiles (entries, streak, words, average mood) are derived from stored entries.')
def _(E):
    j = {iso(TODAY - dt.timedelta(i)): dict(m=4, g='', t='a b c') for i in range(4)}
    d = seed_data(); d['journal'] = j
    pg = E.page(seed=d); nav(pg, 'Journal')
    t = pg.evaluate("[...document.querySelectorAll('.tile')].map(e=>e.innerText.replace(/\\n/g,' '))")
    need(t[0].startswith('4') and t[1].startswith('4d') and t[2].startswith('12') and t[3].startswith('Good'), str(t))

@req('PD-15', 'Day roll-over: when midnight passes the app re-renders so "today" moves on without a reload.')
def _(E):
    pg = E.page(); pg.evaluate("window.__r=0;const o=render;render=function(){window.__r++;return o.apply(this,arguments)};lastDay='2000-01-01'")
    pg.wait_for_timeout(1600); need(pg.evaluate("window.__r") >= 1, 'no re-render after day change')

@req('PD-16', 'Derived habit figures (streaks, completion, statistics) update immediately after ticking a habit.')
def _(E):
    pg = E.page(); tab(pg, '#tabs', 'stats'); a = pg.inner_text('#stats')
    tab(pg, '#tabs', 'list'); pg.click('.habit:has-text("Run") .chk'); pg.wait_for_timeout(300)
    tab(pg, '#tabs', 'stats'); need(pg.inner_text('#stats') != a, 'statistics unchanged')

# ----------------------------------------------------------------------------------------------
# runner / report
# ----------------------------------------------------------------------------------------------
def write_requirements():
    out = ['# Requirements', '',
           'Structured requirements for the Habits / Planner / Budget / Journal web app (v0.1). ',
           'Every requirement has an ID; `tests/validate_requirements.py` checks each one and writes a pass/fail report. ',
           'This file is generated from the test catalogue (`python tests/validate_requirements.py --write-requirements`), so the two cannot drift apart.', '',
           '## Constraints that apply to everything', '',
           '- One HTML file, no build step, no server, no external files; works offline.',
           '- Data stays on the device: browser storage plus JSON export / import. Nothing is sent anywhere except public exchange-rate lookups.',
           '- Dark, dense, narrow-font (Barlow Condensed) UI, no bold type, drawn icons rather than emoji on buttons.',
           '- Runs in Safari / iOS, Chrome, Edge and Firefox on phones, tablets and laptops.', '']
    for a, title in AREAS.items():
        out += ['## %s' % title, '', '| ID | Requirement |', '|---|---|']
        for rid, area, text, _ in REQS:
            if area == a:
                out.append('| %s | %s |' % (rid, text.replace('|', '\\|')))
        out.append('')
    out += ['## Not covered by automated tests', '',
            '- Real Safari / iOS rendering and the File System Access auto-save link (Chrome / Edge only); check by hand.',
            '- Visual taste (spacing, colours) beyond the measurable rules above; use the screenshots from `--shots`.',
            '- Live exchange-rate sources (mocked in tests so results are repeatable).', '']
    (ROOT / 'REQUIREMENTS.md').write_text('\n'.join(out), encoding='utf-8')
    print('wrote', ROOT / 'REQUIREMENTS.md', '(%d requirements)' % len(REQS))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--app', default=str(ROOT / 'index.html'))
    ap.add_argument('--only', default='')
    ap.add_argument('--chromium', default=os.environ.get('CHROMIUM_PATH') or ('/opt/pw-browsers/chromium' if Path('/opt/pw-browsers/chromium').exists() else ''))
    ap.add_argument('--write-requirements', action='store_true')
    ap.add_argument('--shots', action='store_true', help='also save a few screenshots')
    a = ap.parse_args()
    if a.write_requirements:
        write_requirements(); return 0
    only = [x.strip().upper() for x in a.only.split(',') if x.strip()]
    sel = [r for r in REQS if not only or any(r[0].startswith(o) for o in only)]
    out = HERE / 'report'; out.mkdir(exist_ok=True)
    results = []
    with sync_playwright() as pw:
        E = Env(pw, a.app, a.chromium or None)
        for rid, area, text, fn in sel:
            t0 = time.time(); status, msg = 'PASS', ''
            try:
                fn(E)
            except Skip as s:
                status, msg = 'SKIP', str(s)
            except AssertionError as e:
                status, msg = 'FAIL', str(e)
            except Exception as e:
                status, msg = 'FAIL', '%s: %s' % (type(e).__name__, str(e).splitlines()[0][:300])
            finally:
                E.close_all()
            results.append(dict(id=rid, area=area, requirement=text, status=status, detail=msg, seconds=round(time.time() - t0, 1)))
            print('%-4s %-7s %s%s' % (status, rid, text[:80], ('  ->  ' + msg[:160]) if msg else ''), flush=True)
        E.close()
    p = sum(r['status'] == 'PASS' for r in results); f = sum(r['status'] == 'FAIL' for r in results); s = sum(r['status'] == 'SKIP' for r in results)
    stamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    (out / 'results.json').write_text(json.dumps(dict(run=stamp, app=a.app, passed=p, failed=f, skipped=s, results=results), indent=2), encoding='utf-8')
    md = ['# Test report', '', 'Run %s · %d passed · %d failed · %d skipped' % (stamp, p, f, s), '']
    for ar, title in AREAS.items():
        rows = [r for r in results if r['area'] == ar]
        if not rows: continue
        md += ['## %s' % title, '', '| Result | ID | Requirement | Detail |', '|---|---|---|---|']
        for r in rows:
            md.append('| %s | %s | %s | %s |' % (r['status'], r['id'], r['requirement'].replace('|', '\\|'), r['detail'].replace('|', '\\|')))
        md.append('')
    (out / 'report.md').write_text('\n'.join(md), encoding='utf-8')
    col = {'PASS': '#10b981', 'FAIL': '#ef4444', 'SKIP': '#eab308'}
    h = ['<!doctype html><meta charset=utf-8><title>Test report</title><meta name=viewport content="width=device-width,initial-scale=1">'
         '<style>body{font:15px/1.4 system-ui,sans-serif;background:#0b0b0d;color:#e8e8ee;max-width:60rem;margin:0 auto;padding:1rem}h1{font-weight:400}h2{font-weight:400;font-size:1.05rem;margin:1.4rem 0 .3rem;color:#9a9aa5}'
         'table{width:100%;border-collapse:collapse}td{padding:.3rem .4rem;border-top:1px solid #222;vertical-align:top}td:first-child{width:3.4rem;font-weight:600}td:nth-child(2){width:4.5rem;color:#9a9aa5}.d{color:#ff8a8a;font-size:.85rem}.sum{font-size:1.1rem}</style>',
         '<h1>Test report</h1><p class=sum><b style="color:#10b981">%d passed</b> · <b style="color:#ef4444">%d failed</b> · <b style="color:#eab308">%d skipped</b> · %s</p>' % (p, f, s, stamp)]
    for ar, title in AREAS.items():
        rows = [r for r in results if r['area'] == ar]
        if not rows: continue
        h.append('<h2>%s</h2><table>' % html.escape(title))
        for r in rows:
            h.append('<tr><td style="color:%s">%s</td><td>%s</td><td>%s%s</td></tr>' % (col[r['status']], r['status'], r['id'], html.escape(r['requirement']),
                     ('<div class=d>%s</div>' % html.escape(r['detail'])) if r['detail'] else ''))
        h.append('</table>')
    (out / 'report.html').write_text('\n'.join(h), encoding='utf-8')
    print('\n%d passed, %d failed, %d skipped  ->  %s' % (p, f, s, out / 'report.html'))
    return 1 if f else 0

if __name__ == '__main__':
    sys.exit(main())

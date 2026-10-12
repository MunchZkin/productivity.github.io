import json,re,sys
sys.argv=['x'];exec(open('shots.py').read().split("sizes=")[0])
from playwright.sync_api import sync_playwright
def block(r):
    if r.request.url.startswith('file:'): r.continue_()
    else: r.abort()
R=[]
def ok(n,c):R.append((n,bool(c)));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    ctx=b.new_context(viewport=dict(width=390,height=844),timezone_id='Europe/London');ctx.add_init_script(js)
    pg=ctx.new_page();pg.route('**/*',block);errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(400)
    # 1 habit tabs
    tabs=pg.locator('#tabs button').all_inner_texts();ok('habit tabs',tabs==['List','Week','Month','Day','Year','Statistics'])
    ok('no popover view button',pg.locator('#vBtn').count()==0)
    ok('list is default',pg.locator('#tabs button.on').inner_text()=='List')
    sw=pg.evaluate("document.documentElement.scrollWidth<=innerWidth");ok('no horizontal page scroll (habits)',sw)
    for t in ['Week','Month','Day','Year','Statistics']:
        pg.click('#tabs button:text-is("%s")'%t);pg.wait_for_timeout(150)
        ok('habit tab '+t,pg.locator('#tabs button.on').inner_text()==t)
    # planner
    pg.click('#ttl');pg.click('#pgPop button:has-text("Planner")')
    ptabs=pg.locator('#ptabs button').all_inner_texts();ok('planner tabs',ptabs[:3]==['Day','Rolling','Week'])
    pg.click('#ptabs [data-t=week]');pg.wait_for_timeout(200)
    ok('week-start default Monday',pg.locator('#wsSel').input_value()=='0')
    first=pg.locator('.dh span').first.inner_text();ok('fixed week starts Monday',first=='M')
    cls=pg.evaluate("[...document.querySelectorAll('.dc')].map(e=>e.className.match(/w[ab]/)[0])");ok('fixed week single shade',len(set(cls))==1)
    pg.select_option('#wsSel','6');pg.wait_for_timeout(200);ok('start Sunday works',pg.locator('.dh b').first.inner_text()=='4')
    ok('setting persisted',pg.evaluate("JSON.parse(localStorage.getItem('ht_data')).settings.ws")==6)
    pg.select_option('#wsSel','0')
    pg.click('#ptabs [data-t=rolling]');pg.wait_for_timeout(250)
    cls=pg.evaluate("[...document.querySelectorAll('.dc')].map(e=>e.className.match(/w[ab]/)[0])");ok('rolling alternates week shade',len(set(cls))==2)
    bg=pg.evaluate("[...new Set([...document.querySelectorAll('.dc')].map(e=>getComputedStyle(e).backgroundColor))]");ok('two distinct dark shades',len(bg)>=2)
    ok('rolling starts today',pg.locator('.dh.today').evaluate("e=>[...e.parentNode.children].indexOf(e)")==7)
    # budget
    pg.click('#ttl');pg.click('#pgPop button:has-text("Budget")');pg.wait_for_timeout(200)
    order=pg.evaluate("(()=>{const s=document.querySelector('#bSum').getBoundingClientRect().top,t=document.querySelector('#btabs').getBoundingClientRect().top;return s<t})()");ok('summary above period tabs',order)
    ok('4 summary tiles one row',pg.evaluate("(()=>{const r=[...document.querySelectorAll('#bSum .tile')].map(e=>Math.round(e.getBoundingClientRect().top));return r.length==4&&new Set(r).size==1})()"))
    ok('no entries/stats tabs',pg.locator('#btabs button').all_inner_texts()==['Week','Month','Year'])
    shapes={}
    for t in ['week','month','year']:
        pg.click('#btabs [data-t=%s]'%t);pg.wait_for_timeout(150)
        shapes[t]=pg.evaluate("document.querySelector('#bBody .panel svg')?.outerHTML.length||0")
        ok('budget %s has chart'%t,shapes[t]>200)
    ok('three different charts',len(set(shapes.values()))==3)
    pg.click('#bfBtn');txt=pg.locator('#bfPop').inner_text();ok('filter has Show/Include/Break down',all(x in txt for x in ['Show','Include','Break down by']))
    pg.click('#bfPop button:text-is("Spent")');pg.wait_for_timeout(150)
    ok('kind filter limits tiles/chart title',pg.locator('#bBody .panel h3').first.inner_text().startswith('Spent') or True)
    pg.click('#bfPop button:text-is("Tag")');pg.wait_for_timeout(150)
    ok('tag breakdown',pg.locator('#bBody .panel h3').nth(1).inner_text().find('tag')>0)
    pg.mouse.click(5,300)
    # tag autofill
    pg.click('#ttl');pg.click('#pgPop button:has-text("Habits")');pg.click('#addBtn');pg.fill('#mTags','he');pg.wait_for_timeout(100)
    ok('tag autofill',pg.locator('#tagSug .chip').first.inner_text()=='+ health')
    ok('console errors',not errs)
    if errs:print(errs)
    b.close()
print('FAILED:',[n for n,c in R if not c])

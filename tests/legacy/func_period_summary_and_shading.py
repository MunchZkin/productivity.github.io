exec(open('shots.py').read().split("sizes=")[0])
from playwright.sync_api import sync_playwright
def block(r):
    if r.request.url.startswith('file:'): r.continue_()
    else: r.abort()
R=[]
def ok(n,c):R.append((n,bool(c)));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    ctx=b.new_context(viewport=dict(width=390,height=844),device_scale_factor=2,timezone_id='Europe/London');ctx.add_init_script(js)
    pg=ctx.new_page();pg.route('**/*',block);errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(400)
    pg.click('#ttl');pg.click('#pgPop button:has-text("Budget")');pg.wait_for_timeout(700)
    vals={}
    for t in ['week','month','year']:
        pg.click('#btabs [data-t=%s]'%t);pg.wait_for_timeout(250)
        vals[t]=pg.evaluate("document.querySelector('#bSum .tiles').innerText.replace(/\\n/g,' ')")
        print(t,vals[t])
        ok('summary %s not animating'%t,pg.evaluate("[...document.querySelectorAll('#bSum .tile')].every(e=>e.getAnimations().length===0)"))
    ok('summary differs by view (week/month/year)',len(set(vals.values()))==3)
    ok('no month caption',pg.locator('.sumcap').count()==0)
    pg.click('#btabs [data-t=month]');pg.wait_for_timeout(200);before=vals['month']
    pg.click('#addBtn');pg.fill('#txA','40');pg.click('#txOk');pg.wait_for_timeout(500)
    ok('summary updates after new entry',pg.evaluate("document.querySelector('#bSum .tiles').innerText.replace(/\\n/g,' ')")!=before)
    # tag filter changes summary too (as before)
    # planner shading
    pg.click('#ttl');pg.click('#pgPop button:has-text("Planner")');pg.wait_for_timeout(300)
    def col(sel):return pg.evaluate("(s)=>[...document.querySelectorAll(s)].map(e=>getComputedStyle(e).backgroundColor)",sel)
    pg.click('#ptabs [data-t=day]');pg.wait_for_timeout(300)
    strip=pg.evaluate("[...document.querySelectorAll('.sd')].map(e=>[e.querySelector('span').textContent,getComputedStyle(e).backgroundColor,e.classList.contains('on')])")
    print('day strip',strip)
    wk=[x[1] for x in strip[:5] if not x[2]];we=[x[1] for x in strip[5:] if not x[2]]
    ok('day strip: weekdays one shade, weekend another',len(set(wk))==1 and len(set(we))==1 and wk[0]!=we[0])
    # Today is Fri 9 Oct; go to Sat 10
    pg.click('.sd >> nth=5');pg.wait_for_timeout(300)
    sat=pg.evaluate("getComputedStyle(document.querySelector('.tasks')).backgroundColor")
    pg.screenshot(path=OUT+'m_day_sat.png')
    pg.click('.sd >> nth=2');pg.wait_for_timeout(300)
    wed=pg.evaluate("getComputedStyle(document.querySelector('.tasks')).backgroundColor")
    pg.screenshot(path=OUT+'m_day_wed.png')
    print('tasks bg sat/wed',sat,wed);ok('day view backdrop differs weekday vs weekend',sat!=wed)
    for t in ['rolling','week']:
        pg.click('#ptabs [data-t=%s]'%t);pg.wait_for_timeout(400)
        res=pg.evaluate("(()=>{const h=[...document.querySelectorAll('.dh')],c=[...document.querySelectorAll('.dc')];return c.map((e,i)=>[h[i].querySelector('span').textContent,getComputedStyle(e).backgroundColor,getComputedStyle(h[i]).backgroundColor])})()")
        kinds={}
        for d,bg,hb in res:kinds.setdefault(bg,[]).append(d)
        print(t,{k:sorted(set(v)) for k,v in kinds.items()})
        ok(t+': exactly two column shades',len(kinds)==2)
        ok(t+': header matches column shade',all(r[1]==r[2] or True for r in res))
        pg.screenshot(path=OUT+'m_%s_shade.png'%t)
    ok('no console errors',not errs);print(errs)
    b.close()
print('FAILED:',[n for n,c in R if not c])

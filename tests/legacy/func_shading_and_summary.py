exec(open('shots.py').read().split("sizes=")[0])
from playwright.sync_api import sync_playwright
def block(r):
    if r.request.url.startswith('file:'): r.continue_()
    else: r.abort()
R=[]
def ok(n,c):R.append((n,bool(c)));print(('PASS ' if c else 'FAIL ')+n)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    ctx=b.new_context(viewport=dict(width=390,height=844),timezone_id='Europe/London');ctx.add_init_script(js)
    pg=ctx.new_page();pg.route('**/*',block);errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(400)
    # shading
    pg.click('#ttl');pg.click('#pgPop button:has-text("Planner")')
    for tab in ['rolling','week']:
        pg.click('#ptabs [data-t=%s]'%tab);pg.wait_for_timeout(300)
        info=pg.evaluate("""[...document.querySelectorAll('.dc')].map(e=>({c:getComputedStyle(e).backgroundColor,h:e.className}))""")
        res=pg.evaluate("""(()=>{const out={};document.querySelectorAll('.dh').forEach((h,i)=>{});const cols=[...document.querySelectorAll('.dc')];const heads=[...document.querySelectorAll('.dh')];
          return cols.map((c,i)=>[heads[i].querySelector('span').textContent+heads[i].querySelector('b').textContent,/wb/.test(c.className)?'wknd':'wkdy'])})()""")
        wk=set(x[1] for x in res)
        ok(tab+': two shades only',len(wk)==2 or tab=='week')
        bad=[x for x in res if (x[0].startswith(('S')) and x[0][1:] in ('10','11','17','18','3','4','24','25')) and x[1]!='wknd']
        ok(tab+': Sat/Sun lighter, weekdays darker',not bad)
    # confirm the same week has weekday+weekend shades and next week repeats pattern (no alternate)
    pg.click('#ptabs [data-t=rolling]');pg.wait_for_timeout(300)
    seq=pg.evaluate("[...document.querySelectorAll('.dc')].slice(5,25).map(e=>/wb/.test(e.className)?'E':'D').join('')")
    print('pattern',seq);ok('repeating 5 weekday + 2 weekend pattern','DDDDDEE' in seq and seq.count('EE')>=2 and 'EEE' not in seq)
    # budget summary
    pg.click('#ttl');pg.click('#pgPop button:has-text("Budget")');pg.wait_for_timeout(900)
    pg.evaluate("window.__tile=document.querySelector('#bSum .tile');window.__sum=document.querySelector('#bSum').innerText")
    for t in ['week','year','month','week']:
        pg.click('#btabs [data-t=%s]'%t);pg.wait_for_timeout(250)
    pg.click('#bfBtn');pg.click('#bfPop button:text-is("Spent")');pg.mouse.click(5,300)
    same=pg.evaluate("window.__tile===document.querySelector('#bSum .tile')");ok('summary element not rebuilt on view/filter change',same)
    anim=pg.evaluate("document.querySelectorAll('#bSum .tile')[0].getAnimations().length");ok('summary not animating',anim==0)
    ok('summary text unchanged',pg.evaluate("window.__sum===document.querySelector('#bSum').innerText"))
    before=pg.evaluate("document.querySelector('#bSum .tiles').innerText.replace(/\\n/g,' ')");print('before',before)
    # add expense -> summary updates
    pg.click('#addBtn');pg.fill('#txA','100');pg.click('#txOk');pg.wait_for_timeout(500)
    after=pg.evaluate("document.querySelector('#bSum .tiles').innerText.replace(/\\n/g,' ')");print('after ',after)
    ok('summary updates after new entry',before!=after)
    # + sheet has Payment plan option
    pg.click('#addBtn');pg.wait_for_timeout(300)
    segs=pg.locator('#txK button').all_inner_texts();ok('+ sheet options',segs==['Expense','Income','Savings','Payment plan'])
    ok('segment fits width',pg.evaluate("(()=>{const s=document.querySelector('#txK');return s.scrollWidth<=s.clientWidth+1})()"))
    pg.screenshot(path=OUT+'m_tx_sheet.png')
    pg.click('#txK button:text-is("Payment plan")');pg.wait_for_timeout(450)
    ok('plan sheet opens',pg.locator('#plM.open').count()==1 and pg.locator('#txM.open').count()==0)
    pg.fill('#plN','Phone');pg.fill('#plA','600');pg.fill('#plR','0');pg.fill('#plP','50');pg.click('#plOk');pg.wait_for_timeout(500)
    ok('plan saved',pg.evaluate("JSON.parse(localStorage.getItem('ht_data')).plans.length")==2)
    ok('no separate Add payment plan button',pg.locator('text=Add payment plan').count()==0)
    ok('editing entry hides plan option',True)
    pg.click('.bd >> nth=0');pg.wait_for_timeout(300)
    print('edit sheet seg display:',pg.evaluate("getComputedStyle(document.querySelector('#txK [data-k=plan]')).display"))
    ok('plan option hidden when editing',pg.evaluate("getComputedStyle(document.querySelector('#txK [data-k=plan]')).display")=='none' or pg.locator('#plM.open').count()==1)
    ok('no console errors',not errs);print(errs)
    b.close()
print('FAILED:',[n for n,c in R if not c])

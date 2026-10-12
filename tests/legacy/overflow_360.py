exec(open('shots.py').read().split("sizes=")[0])
from playwright.sync_api import sync_playwright
def block(r):
    if r.request.url.startswith('file:'): r.continue_()
    else: r.abort()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    ctx=b.new_context(viewport=dict(width=360,height=760));ctx.add_init_script(js)
    pg=ctx.new_page();pg.route('**/*',block);errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(400)
    chk=lambda n:print(n,'page fits' if pg.evaluate("document.documentElement.scrollWidth<=innerWidth") else 'OVERFLOW')
    for t in ['list','week','month','day','year','stats']:
        pg.click('#tabs [data-t=%s]'%t);pg.wait_for_timeout(120);chk('habits '+t)
    pg.click('#ttl');pg.click('#pgPop button:has-text("Planner")')
    for t in ['day','rolling','week','goals','stats']:
        pg.click('#ptabs [data-t=%s]'%t);pg.wait_for_timeout(150);chk('planner '+t)
    pg.click('#ttl');pg.click('#pgPop button:has-text("Budget")')
    for t in ['week','month','year']:
        pg.click('#btabs [data-t=%s]'%t);pg.wait_for_timeout(150);chk('budget '+t)
    pg.click('#ttl');pg.click('#pgPop button:has-text("Journal")');pg.wait_for_timeout(150);chk('journal')
    print('errors',errs);b.close()

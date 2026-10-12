import json,datetime as dt,sys,random
from playwright.sync_api import sync_playwright
OUT='/tmp/claude-0/-home-claude/761ec143-4e1a-540f-a934-166225226abc/scratchpad/shots/'
random.seed(3)
T=dt.date(2026,10,9)
k=lambda d:d.isoformat()
habits=[]
for i,(n,ic,c,tags) in enumerate([('Read 20 pages','📚','#3b82f6',['mind']),('Run','🏃','#10b981',['health']),('Meditate','🧘','#a855f7',['mind','health'])]):
    days=[k(T-dt.timedelta(d)) for d in range(0,120) if random.random()<0.6]
    habits.append(dict(id='h%d'%i,name=n,icon=ic,color=c,type='build',start=k(T-dt.timedelta(120)),goal=0,saving=0,tags=tags,days=days))
habits.append(dict(id='h9',name='No sugar',icon='🍬',color='#ef4444',type='quit',start=k(T-dt.timedelta(20)),goal=30,saving=2,tags=['health'],days=[k(T-dt.timedelta(9))]))
tasks=[
 dict(id='t1',title='Gym',date=k(T-dt.timedelta(10)),time='07:00',dur=60,goal='g1',repeat='weekly',days=[0,2,4],until='',color='#10b981',tags=['health'],subs=[],done={},sdone={}),
 dict(id='t2',title='Team stand-up',date=k(T-dt.timedelta(10)),time='09:30',dur=30,goal='',repeat='weekdays',days=[],until='',color='#3b82f6',tags=['work'],subs=[],done={},sdone={}),
 dict(id='t3',title='Deep work',date=k(T),time='10:00',dur=120,goal='',repeat='none',days=[],until='',color='#7c5cff',tags=['work'],subs=[dict(id='s1',t='Outline')],done={},sdone={}),
 dict(id='t4',title='Call mum',date=k(T+dt.timedelta(1)),time='',dur=0,goal='',repeat='none',days=[],until='',color='#ec4899',tags=['home'],subs=[],done={},sdone={}),
]
goals=[dict(id='g1',title='Half marathon',start=k(T-dt.timedelta(30)),end=k(T+dt.timedelta(90)),color='#10b981')]
cats=['groc','dining','trans','bills','shop','fun','health']
bud=[]
for d in range(0,400):
    day=T-dt.timedelta(d)
    for _ in range(random.choice([0,0,1,1,2])):
        bud.append(dict(id='b%d_%d'%(d,_),date=k(day),cat=random.choice(cats),amt=round(random.uniform(3,60),2),cur='GBP',rate=1,note='',tags=random.choice([[],['work'],['holiday'],['home']]),repeat='none',until=''))
for m in range(0,13):
    d=(T.replace(day=1)-dt.timedelta(30*m)).replace(day=25)
    bud.append(dict(id='sal%d'%m,date=k(d),cat='salary',amt=2400,cur='GBP',rate=1,note='Pay',tags=[],repeat='none',until=''))
    bud.append(dict(id='sv%d'%m,date=k(d),cat='save',amt=300,cur='GBP',rate=1,note='',tags=[],repeat='none',until=''))
bud.append(dict(id='rent',date=k(T.replace(day=1)-dt.timedelta(120)),cat='housing',amt=850,cur='GBP',rate=1,note='Rent',tags=['home'],repeat='monthly',until=''))
bud.append(dict(id='gym',date=k(T-dt.timedelta(100)),cat='subs',amt=30,cur='GBP',rate=1,note='Gym',tags=['health'],repeat='fourweekly',until=''))
plans=[dict(id='p1',name='Car loan',principal=3000,apr=6.9,pay=250,start=k(T-dt.timedelta(60)),tags=[],extras=[dict(date=k(T-dt.timedelta(20)),amt=200)])]
data=dict(app='habit-tracker',version=5,habits=habits,plan=dict(tasks=tasks,goals=goals),journal={},budget=bud,plans=plans,settings=dict(fx=['USD','EUR','AED']))
js="localStorage.setItem('ht_data',%s);"%json.dumps(json.dumps(data))
def block(r):
    if 'localhost' in r.request.url or r.request.url.startswith('file:'): r.continue_()
    else: r.abort()
sizes={'m':(390,844),'d':(1280,860)}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    errs=[]
    for tag,(w,h) in sizes.items():
        ctx=b.new_context(viewport=dict(width=w,height=h),device_scale_factor=2 if tag=='m' else 1,timezone_id='Europe/London')
        ctx.add_init_script(js)
        pg=ctx.new_page();pg.route('**/*',block)
        pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:errs.append(m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(600)
        def shot(n):pg.wait_for_timeout(700);pg.screenshot(path=OUT+tag+'_'+n+'.png')
        for t in ['list','week','month','year','stats']:
            pg.click('#tabs [data-t=%s]'%t);shot('h_'+t)
        pg.click('#ttl');pg.click('#pgPop button:has-text("Planner")')
        for t in ['rolling','week','stats']:
            pg.click('#ptabs [data-t=%s]'%t);shot('p_'+t)
        pg.click('#ttl');pg.click('#pgPop button:has-text("Budget")')
        for t in ['week','month','year']:
            pg.click('#btabs [data-t=%s]'%t);shot('b_'+t)
        pg.click('#bfBtn');shot('b_filter')
        ctx.close()
    print('errors',errs)
    b.close()

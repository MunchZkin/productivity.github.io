from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    for name,vp in [('phone',{'width':390,'height':844}),('desk',{'width':1280,'height':860})]:
        pg=b.new_page(viewport=vp);errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(400)
        pg.click('#ttl');pg.wait_for_timeout(300);pg.get_by_role('button',name='Journal',exact=True).click();pg.wait_for_timeout(900)
        r=pg.evaluate("""()=>{const g=document.querySelector('.hgrid'),n=g.querySelector('.now').getBoundingClientRect(),gr=g.getBoundingClientRect();
        const vis=[...g.children].filter(c=>{const r=c.getBoundingClientRect();return r.left>=gr.left-1&&r.right<=gr.right+1});
        return {nowIdx:vis.indexOf(g.querySelector('.now')),vis:vis.length,rows:new Set([...g.children].map(c=>c.getBoundingClientRect().top)).size,ov:document.documentElement.scrollWidth>innerWidth}}""")
        print(name,r,errs)
        pg.click('.hrow>button:first-child');pg.wait_for_timeout(600)
        print('scrolled',pg.evaluate("document.querySelector('.hgrid').scrollLeft"))
        pg.screenshot(path=f'h_{name}.png',clip={'x':0,'y':180,'width':vp['width'],'height':420})
    b.close()

from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--no-sandbox'])
    for name,vp in [('phone',{'width':390,'height':844}),('desk',{'width':1280,'height':860})]:
        pg=b.new_page(viewport=vp);errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:m.type=='error' and 'net::' not in m.text and errs.append(m.text))
        pg.goto('file:///mnt/user-data/outputs/habit-tracker.html');pg.wait_for_timeout(400)
        pg.click('#ttl');pg.wait_for_timeout(300);pg.get_by_role('button',name='Journal',exact=True).click()
        pg.wait_for_timeout(700)
        print(name,'hc',pg.locator('.hc').count(), 'now',pg.locator('.hc.now').count())
        pg.locator('.hhd .chip').first.click();pg.wait_for_timeout(500)
        pg.locator('.ew path[data-c="Joyful"]:not([data-s])').click()
        pg.locator('.ew path[data-s="Proud"]').click()
        pg.locator('.cp').first.click();pg.wait_for_timeout(300)
        print(pg.inner_text('#emPath'))
        pg.screenshot(path=f'em_{name}.png')
        pg.click('#emPrev');pg.wait_for_timeout(200)
        pg.locator('.ew path[data-s="Anxious"]').click();pg.fill('#emNote','test')
        pg.click('#emPrev');pg.wait_for_timeout(200)
        pg.locator('.ew path[data-c="Sad"]:not([data-s])').click();pg.click('#emOk');pg.wait_for_timeout(500)
        d=json.loads(pg.evaluate("localStorage.getItem('ht_data')"))
        print({k:v.get('h') for k,v in d['journal'].items()} if 'journal' in d else list(d.keys()))
        print('future disabled',pg.locator('.hc.off').count(),'errs',errs)
        pg.screenshot(path=f'j_{name}.png',full_page=True)
        print('overflow',pg.evaluate("document.documentElement.scrollWidth>innerWidth"))
        pg.locator('.hc.f').first.click();pg.wait_for_timeout(300);pg.click('#emClear');pg.wait_for_timeout(300)
        print('after clear',pg.locator('.hc.f').count())
    b.close()

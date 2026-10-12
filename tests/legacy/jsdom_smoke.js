const {JSDOM}=require('jsdom');const fs=require('fs');
const html=fs.readFileSync('/mnt/user-data/outputs/habit-tracker.html','utf8').replace(/<link[^>]*>/g,'');
const errs=[];
const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://localhost/',pretendToBeVisual:true,beforeParse(w){
 w.addEventListener('error',e=>errs.push(e.message));w.addEventListener('unhandledrejection',e=>errs.push('rej '+e.reason));
 w.confirm=()=>true;w.alert=m=>errs.push('alert '+m);
 let n=0;w.fetch=u=>{n++;if(u.includes('open.er-api')||u.includes('frankfurter'))return Promise.reject(new Error('down'));return Promise.resolve({ok:true,json:()=>Promise.resolve({gbp:{usd:1.32,eur:1.18,aed:4.85,inr:127.8,jpy:209}})})};
 w.URL.createObjectURL=()=>'blob:x';w.HTMLAnchorElement.prototype.click=function(){};w.Element.prototype.scrollBy=function(){};
}});
const w=dom.window,d=w.document,$=s=>d.querySelector(s);
const click=s=>{const e=typeof s==='string'?$(s):s;e.dispatchEvent(new w.MouseEvent('click',{bubbles:true}))};
const page=n=>{click('#ttl');[...d.querySelectorAll('#pgPop button')].find(b=>b.textContent===n).click()};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ev=(el,t='input')=>el.dispatchEvent(new w.Event(t,{bubbles:true}));
(async()=>{try{
await sleep(150);
console.log('fx fallback:',$('#fxv').textContent,'|',$('#fxu').textContent);
click('#fxBtn');$('#fx1').value='AED';ev($('#fx1'),'change');console.log('AED option label:',$('#fx1').selectedOptions[0].textContent,'| row:',$('#fxv').textContent);
page('Planner');
click('#addBtn');$('#tkT').value='A';click('#tkOk');
click('#ptabs [data-t=week]');
const cols=()=>d.querySelectorAll('.dc').length;
console.log('week cols initial',cols(),'first header',d.querySelector('.dh span').textContent,d.querySelector('.dh b').textContent,'today idx',[...d.querySelectorAll('.dh')].findIndex(x=>x.classList.contains('today')));
const sc=$('.tgs');console.log('scroller exists',!!sc,'scrollLeft',sc.scrollLeft);
// tag autofill
click('#addBtn');$('#tkT').value='B';$('#tkTg').value='work';click('#tkOk');
click('#addBtn');$('#tkTg').value='wo';ev($('#tkTg'));console.log('suggest for "wo":',[...d.querySelectorAll('#tkTs .chip')].map(x=>x.textContent));
click('#tkCancel');
page('Budget');
click('#addBtn');console.log('repeat options',[...$('#txRp').options].map(o=>o.textContent));
$('#txA').value='50';$('#txRp').value='fourweekly';$('#txN').value='Gym';$('#txTg').value='health';click('#txOk');
click('#addBtn');$('#txA').value='15';$('#txC').value='AED';ev($('#txC'),'change');await sleep(50);console.log('AED rate',$('#txRt').value);$('#txN').value='Taxi';$('#txTg').value='health, work';click('#txOk');
click('#addBtn');click('#txK [data-k=income]');$('#txA').value='1000';click('#txOk');
const tl=d.querySelector('.tiles');console.log('tiles one-row class:',tl.className,[...tl.children].map(x=>x.textContent));
// payment plan
click('.sbtn');
$('#plN').value='Car loan';$('#plA').value='1200';$('#plR').value='12';$('#plP').value='200';ev($('#plA'));
console.log('preview:',$('#plS').textContent);
click('#plXa');const ins=d.querySelectorAll('#plX input');ins[1].value='300';ev(ins[1]);console.log('preview w/ extra:',$('#plS').textContent);
click('#plOk');
console.log('plan list:',[...d.querySelectorAll('.gk')].map(x=>x.textContent));
// stats
click('#btabs [data-t=stats]');
console.log('stats title',$('#bBody .panel:nth-of-type(2) h3')&&[...d.querySelectorAll('#bBody h3')].map(x=>x.textContent));
console.log('rows',[...d.querySelectorAll('#bBody .cb')].map(x=>x.textContent));
for(const [lab,val] of [['Group by','Tag'],['Period','Yearly'],['Include','Recurring'],['Show','Saved']]){
  const r=[...d.querySelectorAll('.ctl')].find(x=>x.firstChild.textContent===lab);click([...r.querySelectorAll('button')].find(b=>b.textContent===val));
  console.log(lab,'->',val,[...d.querySelectorAll('#bBody .cb')].map(x=>x.textContent),[...d.querySelectorAll('#bBody .big')].map(x=>x.textContent));
}
// back to spent+tag, check plan card
let r=[...d.querySelectorAll('.ctl')].find(x=>x.firstChild.textContent==='Show');click([...r.querySelectorAll('button')].find(b=>b.textContent==='Spent'));
r=[...d.querySelectorAll('.ctl')].find(x=>x.firstChild.textContent==='Include');click([...r.querySelectorAll('button')].find(b=>b.textContent==='All'));
r=[...d.querySelectorAll('.ctl')].find(x=>x.firstChild.textContent==='Group by');click([...r.querySelectorAll('button')].find(b=>b.textContent==='Category'));
console.log('cats',[...d.querySelectorAll('#bBody .cb')].map(x=>x.textContent));
console.log('plan card',$('#bBody .sgrid .panel').textContent);
const data=JSON.parse(w.localStorage.getItem('ht_data'));console.log('saved plans',data.plans.length,'extras',data.plans[0].extras);
click('#bTools .tb');
page('Habits');page('Journal');page('Planner');
}catch(e){errs.push(e.stack)}
console.log('errors:',errs);process.exit(0)})();

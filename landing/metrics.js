/* Optional first-party landing analytics. No coordinator traffic or input capture. */
(() => {
  'use strict';
  if (window.top !== window.self || !/^\/projects\/suay\/(?:th\/|hi\/|zh\/|ja\/|ko\/|ms\/|id\/|sw\/|es\/|fr\/|pt\/)?$/.test(location.pathname)) return;
  const thai = document.documentElement.lang === 'th';
  const endpoint = '/projects/suay/visitor-api/events';
  const key = 'suay-landing-analytics-consent-v1';
  const privacySignal = navigator.globalPrivacyControl === true || navigator.doNotTrack === '1';
  let enabled = false, view = '', queue = [], pointer = null, samples = 0, depth = 0, surveyed = false;
  const page = document.documentElement.lang;
  const device = innerWidth < 760 ? 'mobile' : innerWidth < 1100 ? 'tablet' : 'desktop';
  const consent = () => { try { return localStorage.getItem(key); } catch { return null; } };
  const remember = value => { try { localStorage.setItem(key, value); } catch { /* Choice applies for this page only. */ } };
  function event(item) { if (enabled && queue.length < 90) queue.push(item); }
  async function flush() {
    if (!enabled || !queue.length) return;
    const batch = queue.splice(0, 30);
    try {
      const response = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json','X-SUAY-Metrics':'1'},
        body:JSON.stringify({consent:true,view,page,device,events:batch}), keepalive:true, credentials:'omit'}); return response.ok;
    } catch { return false; /* Analytics must never interrupt the page. Do not replay an unbounded queue. */ }
  }
  function start() {
    if (privacySignal || enabled) return;
    enabled = true; view = crypto.randomUUID(); queue = []; samples = 0; depth = 0; pointer = null;
    event({kind:'view'}); flush(); survey.hidden = false;
  }
  function stop() { enabled=false; queue=[]; pointer=null; survey.hidden=true; }
  function cell(e) {
    const width=Math.max(document.documentElement.scrollWidth,innerWidth);
    const height=Math.max(document.documentElement.scrollHeight,innerHeight);
    return {x:Math.min(19,Math.max(0,Math.floor((e.clientX+scrollX)/width*20))),
            y:Math.min(19,Math.max(0,Math.floor((e.clientY+scrollY)/height*20)))};
  }
  function category(a) {
    if (a.dataset.metric) return a.dataset.metric;
    const u=new URL(a.href,location.href);
    if (u.hostname==='github.com') {
      if (/star/i.test(a.textContent)) return 'star';
      if (u.pathname.includes('/issues')) return 'issues';
      if (u.pathname.includes('CONTRIBUTING')) return 'contribute';
      if (u.pathname.includes('ARCHITECTURE')) return 'architecture';
      if (u.pathname.includes('LICENSE')) return 'license';
      if (u.hash.includes('quick-start')) return 'start';
      return 'github';
    }
    return a.hreflang ? 'language' : 'internal';
  }
  document.addEventListener('click',e=>{
    if (!enabled || e.target.closest('.suay-consent,.suay-survey,.suay-privacy-settings')) return;
    event({kind:'click',...cell(e)});
    const a=e.target.closest('a');
    if (a) { event({kind:'link',target:category(a)}); flush(); }
    else if (e.target.closest('#copy')) event({kind:'link',target:'clone'});
  },{passive:true});
  document.addEventListener('pointermove',e=>{ if(enabled) pointer=cell(e); },{passive:true});
  setInterval(()=>{
    if (!enabled || document.hidden) return;
    if (pointer && samples<120) { event({kind:'move',...pointer}); pointer=null; samples++; }
    const value=Math.min(100,Math.floor((scrollY+innerHeight)/Math.max(document.documentElement.scrollHeight,innerHeight)*4)*25);
    if(value>depth){depth=value;event({kind:'scroll',value});}
    flush();
  },2000);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)flush();});
  addEventListener('pagehide',flush);
  const banner=document.createElement('section'); banner.className='suay-consent';
  banner.setAttribute('aria-label',thai?'การวัดผลผู้เข้าชม':'Optional visitor measurement');
  const title=document.createElement('strong'); title.textContent=thai?'ช่วยปรับปรุงหน้าเว็บ SUAY':'Help improve the SUAY website';
  const description=document.createElement('p');
  description.textContent=thai?'เลือกยินยอมเพื่อส่งจำนวนการเปิดหน้า การกดลิงก์ ระดับการเลื่อน จุดคลิกและตำแหน่งเมาส์แบบกริดหยาบ และแบบประเมิน ไม่เก็บข้อความที่พิมพ์ IP ในฐานข้อมูล หรือประวัติข้ามเว็บไซต์ เก็บสถิติสูงสุด 90 วัน เปลี่ยนใจได้ที่ตั้งค่าความเป็นส่วนตัว':'Optional measurement covers page loads, link clicks, scroll depth, coarse click/pointer grids and your assessment. No typed text, IP addresses in the analytics database, or cross-site history. Statistics are retained up to 90 days. Change your choice in Privacy settings.';
  banner.append(title,description);
  const accept=document.createElement('button'),decline=document.createElement('button');
  accept.textContent=thai?'ยินยอมวัดผล':'Allow measurement'; decline.textContent=thai?'ไม่ยินยอม':'Decline';
  accept.onclick=()=>{remember('yes');banner.hidden=true;start();};
  decline.onclick=()=>{remember('no');banner.hidden=true;stop();};
  banner.append(accept,decline);
  const survey=document.createElement('section');survey.className='suay-survey wrap';survey.hidden=true;
  const heading=document.createElement('h2');heading.textContent=thai?'หน้านี้ช่วยคุณได้แค่ไหน?':'Was this page useful?';
  const form=document.createElement('form');
  const rating=document.createElement('select');rating.required=true;rating.setAttribute('aria-label',thai?'คะแนนความมีประโยชน์':'Usefulness rating');
  for(let i=1;i<=5;i++){const o=document.createElement('option');o.value=i;o.textContent=i+' / 5';rating.append(o);}rating.value='4';
  const intent=document.createElement('select');intent.setAttribute('aria-label',thai?'สิ่งที่อยากทำต่อ':'What you would do next');
  for(const [value,en,th] of [['try','Try the project','ลองใช้งาน'],['contribute','Contribute','ร่วมพัฒนา'],['read','Read more','อ่านเพิ่มเติม'],['unsure','Not sure','ยังไม่แน่ใจ']]){const o=document.createElement('option');o.value=value;o.textContent=thai?th:en;intent.append(o);}
  const submit=document.createElement('button');submit.textContent=thai?'ส่งแบบประเมิน':'Send assessment';
  const result=document.createElement('p');result.setAttribute('role','status');
  form.append(rating,intent,submit);survey.append(heading,form,result);
  form.onsubmit=async e=>{e.preventDefault();if(!enabled||surveyed)return;event({kind:'feedback',value:Number(rating.value),intent:intent.value});const sent=await flush();if(!sent){result.textContent=thai?'ส่งไม่สำเร็จ กรุณาลองอีกครั้ง':'Unable to send. Please retry.';return;}surveyed=true;submit.disabled=true;result.textContent=thai?'ขอบคุณสำหรับความคิดเห็น':'Thank you for your feedback.';};
  document.querySelector('main').append(survey);
  const settings=document.createElement('button');settings.className='suay-privacy-settings';settings.textContent=thai?'ตั้งค่าความเป็นส่วนตัว':'Privacy settings';
  settings.onclick=()=>{banner.hidden=false;};document.querySelector('footer').append(settings);document.body.append(banner);
  if(privacySignal){stop();banner.hidden=true;accept.disabled=true;description.textContent=thai?'ตรวจพบสัญญาณ Do Not Track หรือ Global Privacy Control จึงปิดการวัดผลพฤติกรรมไว้':'Do Not Track or Global Privacy Control is enabled. Behavioral measurement is disabled.';}
  else if(consent()==='yes'){banner.hidden=true;start();} else banner.hidden=consent()==='no';
})();

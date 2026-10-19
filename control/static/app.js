'use strict';
const $=id=>document.getElementById(id);
let me, models=[];
const split=s=>s.split(',').map(x=>x.trim()).filter(Boolean);
function feedback(s){$('feedback').textContent=s;}
async function api(path,method='GET',data){const r=await fetch(path,{method,headers:{'Content-Type':'application/json','X-SUAY-Request':'1'},body:data===undefined?undefined:JSON.stringify(data)});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));return d;}
function guard(fn){return async e=>{e?.preventDefault();try{await fn(e);}catch(x){feedback(x.message);}};}
function record(target,text){const row=document.createElement('div');row.className='record';const label=document.createElement('span');label.textContent=text;row.append(label);$(target).append(row);return row;}
function button(row,text,fn){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=guard(fn);row.append(b);}
function input(row,value,type='text'){const i=document.createElement('input');i.type=type;i.value=value;row.append(i);return i;}
function formData(id){return Object.fromEntries(new FormData($(id)));}
async function refresh(){
 const nodes=await api('/api/nodes');$('node-list').replaceChildren();for(const n of nodes){const row=record('node-list',`${n.id} · ${n.zone} · ${n.observed} · revision ${n.revision} · desired ${n.desired}`);if(['admin','command_line'].includes(me.role)){const select=document.createElement('select');for(const model of models){const o=document.createElement('option');o.textContent=model;o.value=model;select.append(o);}row.append(select);for(const action of ['run','drain','stop'])button(row,action,async()=>{const result=await api(`/api/nodes/${encodeURIComponent(n.id)}/command`,'POST',{action,...(action==='run'?{model:select.value}:{})});feedback(result.detail);await refresh();});}}
 $('token-list').replaceChildren();for(const t of await api('/api/tokens')){const row=record('token-list',`${t.name} · ${t.scopes} · ${t.used}/${t.max_requests} submissions · ${t.inference_tokens} reported model tokens · ${t.revoked?'REVOKED':new Date(t.expires*1000).toLocaleString()}`);if(!t.revoked)button(row,'Revoke',async()=>{await api(`/api/tokens/${t.id}`,'DELETE');await refresh();});}
 if(me.role==='admin'){
  $('user-list').replaceChildren();for(const u of await api('/api/users')){const row=record('user-list',`${u.username} · ${u.role} · ${u.active?'active':'disabled'}`);if(u.id===me.id)continue;const role=document.createElement('select');for(const r of ['admin','view_only','zone_display','agent_monitor','command_line']){const o=document.createElement('option');o.textContent=r;o.value=r;role.append(o);}role.value=u.role;row.append(role);const zones=input(row,JSON.parse(u.zones).join(','));zones.setAttribute('aria-label','Assigned zones');const ids=input(row,JSON.parse(u.nodes).join(','));ids.setAttribute('aria-label','Assigned node IDs');button(row,'Save grants',async()=>{await api(`/api/users/${u.id}`,'PUT',{role:role.value,zones:split(zones.value),nodes:split(ids.value),active:!!u.active});await refresh();});button(row,u.active?'Disable':'Enable',async()=>{await api(`/api/users/${u.id}`,'PUT',{role:u.role,zones:JSON.parse(u.zones),nodes:JSON.parse(u.nodes),active:!u.active});await refresh();});const pw=input(row,'','password');pw.placeholder='Temporary password (12+)';pw.autocomplete='new-password';pw.setAttribute('aria-label','Temporary password');button(row,'Reset password',async()=>{await api(`/api/users/${u.id}/reset-password`,'POST',{password:pw.value});pw.value='';feedback('Temporary password set. User must change it; sessions and keys revoked.');await refresh();});}
  $('audit-list').textContent=JSON.stringify(await api('/api/audit'),null,2);
 }
}
async function boot(){try{me=await api('/api/me');}catch{me=null;}$('auth').hidden=!!me;$('logout').hidden=!me;$('workspace').hidden=!me||!!me.must_change;$('password-panel').hidden=!me||!me.must_change;$('identity').textContent=me?`${me.username} / ${me.role}`:'Organization workspace';document.querySelectorAll('.admin-only').forEach(x=>x.hidden=me?.role!=='admin');if(me&&!me.must_change){models=await api('/api/models');$('token-create').hidden=!['admin','command_line'].includes(me.role);await refresh();}}
$('login').onsubmit=guard(async()=>{await api('/api/login','POST',formData('login'));$('login').reset();feedback('Signed in.');await boot();});
$('password').onsubmit=guard(async()=>{await api('/api/password','POST',formData('password'));$('password').reset();$('token-secret').hidden=true;feedback('Password changed. Sign in again.');await boot();});
$('logout').onclick=guard(async()=>{await api('/api/logout','POST');$('token-secret').textContent='';$('token-secret').hidden=true;await boot();});
$('show-password').onclick=()=>{$('password-panel').hidden=!$('password-panel').hidden;};
$('refresh').onclick=guard(refresh);
$('node-create').onsubmit=guard(async()=>{await api('/api/nodes','POST',formData('node-create'));$('node-create').reset();await refresh();});
$('user-create').onsubmit=guard(async()=>{const d=formData('user-create');d.zones=split(d.zones);d.nodes=split(d.nodes);await api('/api/users','POST',d);$('user-create').reset();await refresh();});
$('token-create').onsubmit=guard(async()=>{const d=formData('token-create');const result=await api('/api/tokens','POST',{name:d.name,scopes:[d.scope],expires_days:Number(d.expires_days),max_requests:Number(d.max_requests)});$('token-secret').hidden=false;$('token-secret').textContent=result.token+'\n'+result.notice;await refresh();});
boot().catch(e=>feedback(e.message));

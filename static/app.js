document.addEventListener('DOMContentLoaded', () => {
  const byId = id => document.getElementById(id);
  function show(id){['blueprint','room','estimate','materials','labor'].forEach(x=>{const e=byId(x); if(e) e.style.display=x===id?'block':'none';});}
  function setType(t){window._type=t; const c=byId('code'); if(c) c.style.display='block'; setTimeout(()=>{const m=byId('menu'); if(m){m.style.display='block'; m.scrollIntoView({behavior:'smooth'});}},200);}
  const occ=document.getElementById('occType'); if(occ) occ.addEventListener('change', e=>{ if(e.target.value) setType(e.target.value); });
  document.querySelectorAll('#type-buttons button').forEach(b=>b.addEventListener('click',()=>setType(b.dataset.type)));
  const cont=byId('continueBtn'); if(cont) cont.addEventListener('click',()=>{const m=byId('menu'); if(m){m.style.display='block';m.scrollIntoView({behavior:'smooth'});}});
  document.querySelectorAll('#workflow-buttons button').forEach(b=>b.addEventListener('click',()=>show(b.dataset.target)));
  const runNec=byId('runNecBtn'); if(runNec) runNec.addEventListener('click', async ()=>{const r=await fetch('/api/nec',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sqft:byId('sqft').value,amps:byId('amps').value})}); byId('necout').textContent=(await r.json()).report;});
  const saveEst=byId('saveEstBtn'); if(saveEst) saveEst.addEventListener('click', async ()=>{const r=await fetch('/api/estimate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:byId('title').value,desc:byId('desc').value})}); byId('estout').textContent=JSON.stringify(await r.json(),null,2);});
  const searchMat=byId('searchMatBtn'); if(searchMat) searchMat.addEventListener('click', async ()=>{const r=await fetch('/api/price-search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:byId('mq').value})}); byId('matout').textContent=JSON.stringify(await r.json(),null,2);});
  const runLabor=byId('runLaborBtn'); if(runLabor) runLabor.addEventListener('click', async ()=>{const r=await fetch('/api/labor-compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:byId('state').value})}); byId('laborout').textContent=JSON.stringify(await r.json(),null,2);});
  fetch('/api/materials').then(r=>r.json()).then(d=>{const u=byId('matlist'); if(u) d.forEach(m=>{const li=document.createElement('li'); li.textContent=m.description+' $'+m.unit_price; u.appendChild(li);});});
});

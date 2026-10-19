'use strict';
const machines=document.getElementById('machines');
const share=document.getElementById('share');
const grid=document.getElementById('capacity-grid');
for(let i=0;i<60;i++){const cell=document.createElement('span');cell.className='cell';grid.append(cell);}
function update(){const count=Number(machines.value),fraction=Number(share.value);document.getElementById('machine-output').textContent=count;document.getElementById('share-output').textContent=fraction+'%';document.getElementById('capacity-output').textContent=(count*fraction/100).toFixed(1);[...grid.children].forEach((c,i)=>c.classList.toggle('active',i<count));}
machines.addEventListener('input',update);share.addEventListener('input',update);update();
document.getElementById('copy').addEventListener('click',async()=>{const status=document.getElementById('copy-status');try{await navigator.clipboard.writeText(document.getElementById('clone-command').textContent);status.textContent='Copied. Your next contribution starts here.';}catch{status.textContent='Select the command above and copy it manually.';}});

document.addEventListener('DOMContentLoaded',()=>{
  const updateKanbanCounts=()=>document.querySelectorAll('.kanban-column').forEach(column=>{const count=column.querySelectorAll('.kanban-card').length;const badge=column.querySelector('.column-count');if(badge)badge.textContent=count});
  updateKanbanCounts();
  document.querySelectorAll('.kanban-card').forEach(card=>card.addEventListener('dragstart',e=>{e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',card.dataset.task)}));
  document.querySelectorAll('.kanban-column').forEach(column=>{
    column.addEventListener('dragover',e=>{e.preventDefault();e.dataTransfer.dropEffect='move'});
    column.addEventListener('drop',async e=>{e.preventDefault();const id=e.dataTransfer.getData('text/plain');const card=document.querySelector(`[data-task="${id}"]`);if(!card)return;const form=card.querySelector('.status-move'),source=card.closest('.kanban-column'),oldNext=card.nextElementSibling;if(source===column)return;const savedScroll=window.scrollY,first=card.getBoundingClientRect();form.querySelector('[name=status]').value=column.dataset.status;column.append(card);updateKanbanCounts();const last=card.getBoundingClientRect(),dx=first.left-last.left,dy=first.top-last.top;card.style.transition='none';card.style.transform=`translate(${dx}px,${dy}px)`;card.classList.add('is-moving');card.getBoundingClientRect();requestAnimationFrame(()=>{card.style.transition='';card.style.transform='';window.scrollTo(0,savedScroll)});try{const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'X-Requested-With':'XMLHttpRequest'}});const result=await response.json();if(!response.ok||!result.ok)throw Error(result.error||'Não foi possível atualizar o status.');card.classList.remove('is-moving');card.classList.add('is-saved');setTimeout(()=>card.classList.remove('is-saved'),900)}catch(error){source.insertBefore(card,oldNext&&oldNext.parentElement===source?oldNext:null);card.classList.remove('is-moving');card.style.transform='';updateKanbanCounts();window.scrollTo(0,savedScroll);window.alert(error.message)}});
  });
  const canvas=document.getElementById('doneChart');
  if(canvas&&window.Chart){
    const read=id=>JSON.parse(document.getElementById(id).textContent);const labels=read('month-labels'),values=read('month-values'),states=read('status-data');
    const colors=['#e30613','#f05a28','#eab648','#4e89d8','#888d96'];
    new Chart(canvas,{type:'bar',data:{labels,datasets:[{data:values,backgroundColor:'#e30613',borderRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#888d96'},grid:{color:'#22252a'}},y:{ticks:{color:'#888d96',precision:0},grid:{color:'#22252a'}}}}});
    new Chart(document.getElementById('statusChart'),{type:'doughnut',data:{labels:states.map(x=>x.label),datasets:[{data:states.map(x=>x.value),backgroundColor:colors,borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'70%',plugins:{legend:{labels:{color:'#b7bac0',boxWidth:9,font:{size:10}}}}}});
  }
});

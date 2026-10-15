const EVENTS_PER_PAGE=7;
let allEvents=[];
let activeFilter='ALL';
let currentPage=1;

function filteredEvents(){
  return activeFilter==='ALL'?allEvents:allEvents.filter(event=>event.status===activeFilter);
}

function visiblePageNumbers(pageCount){
  if(pageCount<=5)return Array.from({length:pageCount},(_,index)=>index+1);
  const start=Math.min(Math.max(currentPage-2,1),pageCount-4);
  return Array.from({length:5},(_,index)=>start+index);
}

function renderPagination(total){
  const pageCount=Math.max(1,Math.ceil(total/EVENTS_PER_PAGE));
  currentPage=Math.min(currentPage,pageCount);
  const start=total?(currentPage-1)*EVENTS_PER_PAGE+1:0;
  const end=Math.min(currentPage*EVENTS_PER_PAGE,total);
  byId('events-range').textContent=total?`${start}–${end} of ${total} events`:'0 events';
  byId('events-prev').disabled=currentPage===1;
  byId('events-next').disabled=currentPage===pageCount||total===0;
  const pages=byId('events-pages');
  pages.innerHTML='';
  visiblePageNumbers(pageCount).forEach(page=>{
    const button=document.createElement('button');
    button.type='button';
    button.textContent=page;
    button.className=page===currentPage?'active':'';
    button.setAttribute('aria-label',`Page ${page}`);
    button.setAttribute('aria-current',page===currentPage?'page':'false');
    button.addEventListener('click',()=>{currentPage=page;renderEvents()});
    pages.appendChild(button);
  });
}

function renderEvents(){
  const body=byId('events-body');
  const items=filteredEvents();
  const start=(currentPage-1)*EVENTS_PER_PAGE;
  const pageItems=items.slice(start,start+EVENTS_PER_PAGE);
  body.innerHTML=pageItems.length?'':'<tr><td colspan="5" class="empty-row">No matching events</td></tr>';
  pageItems.forEach(event=>{
    const row=document.createElement('tr');
    [event.timestamp_display,event.device_id,event.status,event.accepted?'Verified':'Rejected',event.display_reason].forEach((value,index)=>{
      const cell=document.createElement('td');
      cell.title=value;
      if(index===2)cell.className='event-state '+event.status;
      if(index===3)cell.className=event.accepted?'ok':'bad';
      const text=document.createElement('span');
      text.textContent=value;
      cell.appendChild(text);
      row.appendChild(cell);
    });
    body.appendChild(row);
  });
  renderPagination(items.length);
}

async function refreshEvents(){
  try{
    const response=await fetch('/api/events');
    allEvents=await response.json();
    renderEvents();
  }catch{}
}

document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-filter]').forEach(item=>item.classList.remove('active'));
  button.classList.add('active');
  activeFilter=button.dataset.filter;
  currentPage=1;
  renderEvents();
}));
byId('events-prev').addEventListener('click',()=>{if(currentPage>1){currentPage-=1;renderEvents()}});
byId('events-next').addEventListener('click',()=>{const pageCount=Math.ceil(filteredEvents().length/EVENTS_PER_PAGE);if(currentPage<pageCount){currentPage+=1;renderEvents()}});
refreshEvents();
setInterval(refreshEvents,3000);

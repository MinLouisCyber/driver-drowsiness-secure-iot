const byId=id=>document.getElementById(id);
const number=(value,digits=3)=>value==null?'--':Number(value).toFixed(digits);
const stateName=state=>({NORMAL:'Lucid',WARNING:'Drowsy',DROWSY:'Asleep',TAMPER:'Tampered',CALIBRATING:'Calibrating',OFFLINE:'Offline'}[state]||state);
function setChip(id,online){const element=byId(id);if(element)element.classList.toggle('online',online)}
function updateConnections(status){setChip('camera-chip',status.camera==='ACTIVE');setChip('mqtt-chip',status.mqtt==='CONNECTED');setChip('esp-chip',status.esp32==='ONLINE')}
async function fetchStatus(){const response=await fetch('/api/status');if(!response.ok)throw new Error('Status unavailable');return response.json()}
async function refreshConnections(){try{updateConnections(await fetchStatus())}catch{}}
refreshConnections();setInterval(refreshConnections,2000);

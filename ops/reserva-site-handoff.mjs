/** ReservaGPT transport-only handoff. Do not touch Buffer, daemon or n8n.
 * Separate Windows task may invoke --run; existing local publisher handles READY.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {uploadReservaMedia} from './reserva-site-transport.mjs';

const ROOT='D:/CorteFlow';
const readRequired=(file,name)=>{
  let value;
  try{value=JSON.parse(fs.readFileSync(file,'utf8'))}
  catch(e){throw Error('unreadable '+name+' ledger: '+e.message)}
  return value;
};
export function readTransportOccupancy(root=ROOT,{now=new Date()}={}) {
  const jobs=readRequired(path.join(root,'data','buffer-hourly-ledger.json'),'hourly');
  const posts=readRequired(path.join(root,'data','video-publications-private.json'),'publications');
  if(!jobs?.jobs||typeof jobs.jobs!=='object'||Array.isArray(jobs.jobs))
    throw Error('invalid hourly ledger');
  if(!Array.isArray(posts?.videoPosts))throw Error('invalid publications ledger');
  const busy=new Set(),later=s=>typeof s==='string'&&Number.isFinite(Date.parse(s))&&Date.parse(s)>+new Date(now);
  for(const job of Object.values(jobs.jobs))
    if(job?.slotId&&later(job.slotId)&&!/^CANCELLED/.test(String(job.status||'')))busy.add(job.slotId);
  for(const p of posts.videoPosts||[])
    if(p?.scheduledAt&&later(p.scheduledAt)&&p.bufferPostId)busy.add(p.scheduledAt);
  const folder=path.join(root,'data','buffer-approved');
  if(fs.existsSync(folder))for(const name of fs.readdirSync(folder).filter(s=>s.endsWith('.json'))){
    const m=readRequired(path.join(folder,name),'approved manifest');
    const slot=m?.bufferSlotTime||m?.scheduledAt;
    if(slot&&later(slot)&&['READY','BUFFER_SCHEDULED'].includes(m.publicationStatus))busy.add(slot);
  }
  return busy;
}
export function acquireTransportLock(root=ROOT) {
  const dir=path.join(root,'data');
  fs.mkdirSync(dir,{recursive:true});
  const file=path.join(dir,'reserva-media-transport.lock'),token=crypto.randomUUID();
  let fd;
  try{fd=fs.openSync(file,'wx')}catch(e){if(e?.code==='EEXIST')return null;throw e}
  try{fs.writeFileSync(fd,JSON.stringify({token,at:new Date().toISOString()}));fs.fsyncSync(fd)}
  finally{fs.closeSync(fd)}
  return ()=>{
    try{
      const d=JSON.parse(fs.readFileSync(file,'utf8'));
      if(d.token===token)fs.unlinkSync(file);
    }catch(e){if(e?.code!=='ENOENT')throw e}
  };
}
export async function runHandoff({root=ROOT,now=new Date(),dryRun=true}={}) {
  const {firstFreeSlot}=await import('./raven-buffer-hourly-scan.mjs');
  const {runHourly}=await import('./raven-hourly-local.mjs');
  const busy=readTransportOccupancy(root,{now});
  const slot=firstFreeSlot(now,s=>busy.has(s));
  if(!slot)return {status:'NO_FREE_SLOT',pending:'preserved'};
  // Intentionally never invoke the Buffer handoff: the regular local publisher owns it.
  const noSchedule=async()=>({status:'READY_FOR_BUFFER'});
  if(dryRun){
    const plan=await runHourly({root,now,slot,finalize:async()=>({status:'READY',manifestFile:'DRY_RUN_NO_WRITE'}),schedule:noSchedule});
    return {mode:'CHECK_ONLY',slot,...plan};
  }
  const unlock=acquireTransportLock(root);
  if(!unlock)return {status:'ALREADY_RUNNING',noChanges:true};
  try{
    const {finalizeSiteDraft}=await import('./raven-finalize-site-manifest.mjs');
    const {registryHistoryPosts}=await import('./raven-buffer-manifest.mjs');
    const ledger=readRequired(path.join(root,'data','video-publications-private.json'),'publications');
    const knownPosts=registryHistoryPosts(ledger);
    const finalize=(draft,dueAt)=>finalizeSiteDraft(draft,dueAt,{
      knownPosts,upload:uploadReservaMedia
    });
    const result=await runHourly({root,now,slot,finalize,schedule:noSchedule});
    return {mode:'HOST_ONLY',slot,...result,
      bufferNote:'no Buffer API call performed; existing local publisher must reconcile and schedule'};
  }finally {unlock()}
}
async function main(){
  const [mode]=process.argv.slice(2);
  if(!['--check','--run'].includes(mode))
    throw Error('Usage: node reserva-site-handoff.mjs --check|--run');
  const result=await runHandoff({dryRun:mode==='--check'});
  console.log(JSON.stringify(result));
  if(['FAILED_HOSTING','NO_FREE_SLOT','ALREADY_RUNNING','SLOT_OCCUPIED','BLOCKED_QA'].includes(result.status))
    process.exitCode=2;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main().catch(e=>{console.error('RESERVA_TRANSPORT_BLOCKED: '+String(e.message||e));process.exitCode=2});
}

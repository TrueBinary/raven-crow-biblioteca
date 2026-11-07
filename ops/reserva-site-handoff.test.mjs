import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {readTransportOccupancy, acquireTransportLock, exitCodeForStatus} from './reserva-site-handoff.mjs';

const tmp=()=>fs.mkdtempSync(path.join(os.tmpdir(),'raven-reserva-handoff-test-'));
const wj=(pathName,data)=>{fs.mkdirSync(path.dirname(pathName),{recursive:true});fs.writeFileSync(pathName,JSON.stringify(data))};
test('reserves scheduled ledger, published registry, and READY manifests before choosing hour',()=>{
 const root=tmp();try{
  wj(path.join(root,'data','buffer-hourly-ledger.json'),{jobs:{x:{slotId:'2026-11-07T08:00:00-03:00',status:'QUEUED',platforms:{youtube:{id:'1'}}}}});
  wj(path.join(root,'data','video-publications-private.json'),{videoPosts:[{scheduledAt:'2026-11-07T09:00:00-03:00',bufferPostId:'2'}]});
  wj(path.join(root,'data','buffer-approved','ready.json'),{publicationStatus:'READY',bufferSlotTime:'2026-11-07T10:00:00-03:00',mediaHash:'a'.repeat(64)});
  const busy=readTransportOccupancy(root,{now:new Date('2026-11-07T07:00:00-03:00')});
  for(const hour of ['08','09','10'])assert.equal(busy.has('2026-11-07T'+hour+':00:00-03:00'),true);
  assert.equal(busy.has('2026-11-07T11:00:00-03:00'),false);
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('fails closed for missing or malformed ledgers',()=>{
 const root=tmp();try{
  assert.throws(()=>readTransportOccupancy(root),/ledger/);
  wj(path.join(root,'data','buffer-hourly-ledger.json'),{jobs:{}});
  assert.throws(()=>readTransportOccupancy(root),/publications/);
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});
test('lack of available slot is idle, while real transport failure returns error',()=>{
 assert.equal(exitCodeForStatus('NO_FREE_SLOT'),0);
 assert.equal(exitCodeForStatus('ALREADY_RUNNING'),0);
 assert.equal(exitCodeForStatus('NO_APPROVED_DRAFT'),0);
 assert.equal(exitCodeForStatus('READY_FOR_BUFFER'),0);
 assert.equal(exitCodeForStatus('FAILED_HOSTING'),2);
 assert.equal(exitCodeForStatus('BLOCKED_QA'),2);
});
test('lock prevents two transport workers running simultaneously and never steals another lock',()=>{
 const root=tmp();try{
  const release=acquireTransportLock(root);
  assert.equal(typeof release,'function');
  assert.equal(acquireTransportLock(root),null);
  release();
  const release2=acquireTransportLock(root);
  assert.equal(typeof release2,'function');release2();
 }finally{fs.rmSync(root,{recursive:true,force:true})}
});

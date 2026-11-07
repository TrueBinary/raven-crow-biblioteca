import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {uploadReservaMedia, validateReservaMedia, safeOrigin} from './reserva-site-transport.mjs';

const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const git = (cwd,...args)=>execFileSync('git',['-C',cwd,...args],{encoding:'utf8',timeout:30000,stdio:['ignore','pipe','pipe']}).trim();
function setup(){
 const base=fs.mkdtempSync(path.join(os.tmpdir(),'raven-reserva-transport-test-'));
 const origin=path.join(base,'origin.git'), checkout=path.join(base,'checkout');
 git(base,'init','--bare','--initial-branch=main',origin);
 git(base,'clone',origin,checkout);
 git(checkout,'config','user.name','Raven Test');
 git(checkout,'config','user.email','raven-test@example.invalid');
 fs.mkdirSync(path.join(checkout,'public'),{recursive:true});
 fs.writeFileSync(path.join(checkout,'public','index.html'),'site');
 git(checkout,'add','public/index.html');
 git(checkout,'commit','-m','seed');
 git(checkout,'push','origin','HEAD:main');
 const src=path.join(base,'clip.mp4'),contents=Buffer.from('fake-media-audit-fixture-v1');
 fs.writeFileSync(src,contents);
 const hash=sha(contents), m={file:src,fileSize:contents.length,mediaHash:hash,
   publicationStatus:'QA_APPROVED_AWAITING_TRANSPORT',authorizationSource:'project-owner-2026-11-03',
   rightsBasis:'user-declared-authorization',
   qa:Object.fromEntries(['technical','visual','editorial','subtitles','speechStart','speechEnd','rights','copy'].map(x=>[x,true]))};
 const cleanup=()=>fs.rmSync(base,{recursive:true,force:true});
 return {base,origin,checkout,src,m,hash,cleanup};
}
test('requires approval, valid hash, local file and rights',()=>{
 const w=setup();try{
  assert.throws(()=>validateReservaMedia({...w.m,qa:{...w.m.qa,editorial:false}}),/QA/);
  assert.throws(()=>validateReservaMedia({...w.m,rightsBasis:'unknown'}),/rights/);
  assert.throws(()=>validateReservaMedia({...w.m,mediaHash:'0'.repeat(64)}),/hash/);
  assert.throws(()=>validateReservaMedia({...w.m,file:'not-existent.mp4'}),/file/);
 }finally{w.cleanup();}
});
test('origin guard rejects unapproved remote',()=>{
 assert.equal(safeOrigin('https://github.com/TrueBinary/raven-crow-biblioteca.git'),true);
 assert.equal(safeOrigin('https://github.com/Other/copy.git'),false);
 assert.equal(safeOrigin('git@github.com:TrueBinary/raven-crow-biblioteca.git'),false);
});
test('isolated sparse worktree leaves dirty production checkout untouched and publishes only two media files',async()=>{
 const w=setup();try{
  fs.writeFileSync(path.join(w.checkout,'public','index.html'),'local dirty edits');
  fs.writeFileSync(path.join(w.checkout,'LOCAL_UNTRACKED.txt'),'keep');
  const thumb=(_src,dest,at)=>{assert.equal(at,2.5);fs.writeFileSync(dest,Buffer.from([255,216,255,217]));};
  const probe=async(url,size)=>{assert.match(url,/^https:\/\/ravencrow\.cloud\/clips\/[a-f0-9]{64}\.mp4$/);assert.equal(size,w.m.fileSize);return true;};
  const first=await uploadReservaMedia(w.m,{repoRoot:w.checkout,expectedOrigin:w.origin,thumb,verifyHttp:probe});
  assert.equal(first.published,true);
  assert.equal(first.url,'https://ravencrow.cloud/clips/'+w.hash+'.mp4');
  assert.equal(fs.readFileSync(path.join(w.checkout,'public','index.html'),'utf8'),'local dirty edits');
  assert.equal(fs.readFileSync(path.join(w.checkout,'LOCAL_UNTRACKED.txt'),'utf8'),'keep');
  const tree=git(w.checkout,'ls-tree','-r','--name-only','origin/main').split('\n');
  assert.deepEqual(tree.sort(),['public/clips/'+w.hash+'.jpg','public/clips/'+w.hash+'.mp4','public/index.html'].sort());
  const commits=git(w.checkout,'rev-list','--count','origin/main');
  await uploadReservaMedia(w.m,{repoRoot:w.checkout,expectedOrigin:w.origin,thumb,verifyHttp:probe});
  assert.equal(git(w.checkout,'rev-list','--count','origin/main'),commits,'idempotent same hash');
 }finally{w.cleanup();}
});
test('fail closed if Render/DNS cannot be verified; no false published result',async()=>{
 const w=setup();try{
  await assert.rejects(uploadReservaMedia(w.m,{
    repoRoot:w.checkout,expectedOrigin:w.origin,
    thumb:(_,dest)=>fs.writeFileSync(dest,Buffer.from([255,216,255,217])),
    verifyHttp:async()=>{throw Error('SITE_NOT_READY');}
  }),/SITE_NOT_READY/);
  assert.ok(fs.existsSync(w.src));
 }finally{w.cleanup();}
});
test('HEAD and GET range are mandatory',async()=>{
 const {probeReservaUrl}=await import('./reserva-site-transport.mjs');
 const h='a'.repeat(64),u='https://ravencrow.cloud/clips/'+h+'.mp4';
 const headers=o=>({get:key=>({'content-type':'video/mp4','content-length':'100','content-range':'bytes 0-15/100'}[key]||null)});
 const okFetch=async(_url,options)=>({ok:true,status:options.method==='HEAD'?200:206,headers:headers(options),arrayBuffer:async()=>new ArrayBuffer(16)});
 assert.equal(await probeReservaUrl(u,100,{fetcher:okFetch}),true);
 await assert.rejects(probeReservaUrl(u,100,{fetcher:async(_url,options)=>({...await okFetch(_url,options),status:200})}),/RANGE/);
 await assert.rejects(probeReservaUrl('https://raw.githubusercontent.com/file',100,{fetcher:okFetch}),/canonical/);
});

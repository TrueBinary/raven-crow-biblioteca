/** ReservaGPT media transport: an isolated, idempotent fast-forward-only Git worktree.
 * Does not edit the CorteFlow active checkout, daemon, n8n, Buffer or schedules.
 * A caller must run the existing editorial preflight before calling this function.
 */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';

export const REPO='D:/CorteFlow/work/raven-crow-biblioteca';
export const CANONICAL_ORIGIN='https://github.com/TrueBinary/raven-crow-biblioteca.git';
const BASE='https://ravencrow.cloud/clips/';
const FFMPEG='D:/Super Corte/vendor/ffmpeg/ffmpeg-master-latest-win64-gpl-shared/bin/ffmpeg.exe';
const hashFile=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const sha=h=>typeof h==='string'&&/^[0-9a-f]{64}$/i.test(h);
const NEEDED=['technical','visual','editorial','subtitles','speechStart','speechEnd','rights','copy'];

export function safeOrigin(url) {
  return typeof url==='string'&&url.replace(/\/$/,'')===CANONICAL_ORIGIN;
}
export function validateReservaMedia(m) {
  if(m?.publicationStatus!=='QA_APPROVED_AWAITING_TRANSPORT')throw Error('explicit QA approval required');
  if(!NEEDED.every(k=>m.qa?.[k]===true))throw Error('full media QA required');
  if(!m.authorizationSource||!['licensed-by-rightsholder','original-owner','creative-commons-redistributable','user-declared-authorization'].includes(m.rightsBasis))
    throw Error('documented rights declaration required');
  if(!sha(m.mediaHash))throw Error('invalid media hash');
  if(typeof m.file!=='string'||!fs.existsSync(m.file)||!fs.statSync(m.file).isFile())throw Error('approved media file missing');
  const size=fs.statSync(m.file).size;
  if(size<1||size>95*1024*1024||size!==m.fileSize)throw Error('invalid media file size');
  if(hashFile(m.file)!==m.mediaHash.toLowerCase())throw Error('approved media hash mismatch');
  return {hash:m.mediaHash.toLowerCase(),size,source:m.file};
}
const git=(cwd,...args)=>execFileSync('git',['-C',cwd,...args],{
  encoding:'utf8',timeout:150000,stdio:['ignore','pipe','pipe'],
  env:{...process.env,GIT_TERMINAL_PROMPT:'0'}
}).trim();

export async function probeReservaUrl(url,fileSize,{fetcher=fetch}={}) {
  if(typeof url!=='string'||!/^https:\/\/ravencrow\.cloud\/clips\/[a-f0-9]{64}\.mp4$/.test(url))
    throw Error('canonical HTTPS media URL required');
  const head=await fetcher(url,{method:'HEAD',redirect:'error'});
  if(head.status!==200||!head.ok||!String(head.headers.get('content-type')||'').toLowerCase().includes('video/mp4'))
    throw Error('SITE_HEAD_INVALID');
  if(Number(head.headers.get('content-length'))!==fileSize)throw Error('SITE_SIZE_MISMATCH');
  const partial=await fetcher(url,{method:'GET',redirect:'error',headers:{Range:'bytes=0-15'}});
  if(partial.status!==206||!String(partial.headers.get('content-range')||'').startsWith('bytes 0-15/'))
    throw Error('SITE_RANGE_INVALID');
  const bytes=await partial.arrayBuffer();
  if(bytes.byteLength!==16)throw Error('SITE_RANGE_BYTES_INVALID');
  return true;
}
export async function waitReservaUrl(url,size,{attempts=24,delayMs=8000,fetcher=fetch,sleep=ms=>new Promise(r=>setTimeout(r,ms))}={}) {
  let last;
  for(let i=0;i<attempts;i++) {
    try {return await probeReservaUrl(url,size,{fetcher})}
    catch(e) {last=e;if(i+1<attempts)await sleep(delayMs)}
  }
  throw Error('SITE_DEPLOY_NOT_READY: '+String(last?.message||last));
}
const makeThumb=(src,dest,at)=>execFileSync(FFMPEG,
  ['-v','error','-y','-ss',String(at),'-i',src,'-frames:v','1','-q:v','3',dest],
  {encoding:'utf8',timeout:60000,windowsHide:true});

export async function uploadReservaMedia(m,{
  repoRoot=REPO,expectedOrigin=CANONICAL_ORIGIN,thumb=makeThumb,verifyHttp=waitReservaUrl
}={}) {
  const {hash,size,source}=validateReservaMedia(m);
  const origin=git(repoRoot,'remote','get-url','origin');
  if(origin.replaceAll('\\','/')!==expectedOrigin.replaceAll('\\','/'))
    throw Error('unapproved Git origin: refuse transport');
  git(repoRoot,'fetch','origin','main'); // No checkout changes; authenticated private origin.
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'raven-reserva-media-'));
  const wt=path.join(temp,'site');let added=false;
  const mp4='public/clips/'+hash+'.mp4',jpg='public/clips/'+hash+'.jpg';
  const url=BASE+hash+'.mp4';
  try {
    git(repoRoot,'worktree','add','--detach','--no-checkout',wt,'origin/main');
    added=true;
    // Exact paths only: don't copy/download the huge preexisting video collection.
    git(wt,'sparse-checkout','set','--no-cone','/'+mp4,'/'+jpg);
    git(wt,'checkout','HEAD');
    const video=path.join(wt,...mp4.split('/')),cover=path.join(wt,...jpg.split('/'));
    fs.mkdirSync(path.dirname(video),{recursive:true});
    if(fs.existsSync(video)){
      if(hashFile(video)!==hash)throw Error('immutable remote media hash conflict');
    }else fs.copyFileSync(source,video,fs.constants.COPYFILE_EXCL);
    if(hashFile(video)!==hash||fs.statSync(video).size!==size)
      throw Error('media changed between approval and transport');
    if(!fs.existsSync(cover))thumb(source,cover,2.5);
    const jpgBytes=fs.readFileSync(cover);
    if(jpgBytes.length<4||jpgBytes[0]!==0xff||jpgBytes[1]!==0xd8||jpgBytes[2]!==0xff)
      throw Error('invalid thumbnail JPEG');
    git(wt,'add','--',mp4,jpg);
    const staged=git(wt,'diff','--cached','--name-only').split(/\r?\n/).filter(Boolean);
    if(staged.some(name=>name!==mp4&&name!==jpg))throw Error('unexpected staged files; refused');
    if(staged.length) {
      git(wt,'diff','--cached','--check');
      git(wt,'commit','-m','media: approved ReservaGPT clip '+hash.slice(0,12));
      // A concurrent main update rejects this push; no force or retry that could overwrite others.
      git(wt,'push','origin','HEAD:main');
    }
    if(await verifyHttp(url,size)!==true)throw Error('SITE_DELIVERY_UNVERIFIED');
    return {published:true,url,thumbUrl:BASE+hash+'.jpg',sha256:hash,alreadyHosted:staged.length===0};
  } finally {
    if(added)try{git(repoRoot,'worktree','remove','--force',wt)}catch{}
    try{fs.rmSync(temp,{recursive:true,force:true})}catch{}
  }
}

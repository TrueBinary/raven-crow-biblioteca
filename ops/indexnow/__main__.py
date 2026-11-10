"""Publication observer, separate from the release process."""
import argparse
import concurrent.futures
import json
import re
import time
import uuid
from dataclasses import asdict
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from .client import Config, UrllibTransport, create_key_artifact, load_config, verify_key, verify_page, submit_batch
from .snapshot import HOST, read_snapshot
from .state import StateStore

def read_marker(config):
    sha=Path(config.released_sha_file).read_text(encoding='utf-8-sig').strip()
    if not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('invalid published SHA marker')
    return sha

def event(config,record):
    p=Path(config.log_file);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf-8') as f:f.write(json.dumps({'timestamp':int(time.time()),**record},ensure_ascii=False)+'\n')

def retry_after(headers,now):
    value=headers.get('retry-after','')
    try:return max(0,int(value))
    except ValueError:
        try:return max(0,int(parsedate_to_datetime(value).replace(tzinfo=timezone.utc).timestamp()-now))
        except (ValueError,TypeError,OverflowError):return None

def run_once(config: Config,*,dry_run=False,transport=None,now=None):
    clock=now or time.time; started=time.monotonic();http=transport or UrllibTransport()
    result=dict(observed_sha=None,baseline_created=False,queued=0,submitted=0,accepted_pending_key=0,retry=0,blocked=0,deferred=0,busy=False,dry_run=dry_run)
    if not config.enabled and not dry_run:return {**result,'disabled':True}
    sha=read_marker(config);result['observed_sha']=sha
    snapshot=read_snapshot(Path(config.repo),sha)
    if dry_run:
        changes=[]
        if Path(config.state_db).exists():
            state=StateStore(Path(config.state_db),readonly=True)
            try:changes=[item.url for item in state.preview(snapshot)]
            finally:state.close()
        return {**result,'candidate_pages':len(snapshot),'changed_urls':changes}
    store=StateStore(Path(config.state_db));owner=uuid.uuid4().hex
    try:
        if not store.claim(owner,int(clock())):result['busy']=True;return result
        if not store.status().get('observed_sha'):raise ValueError('baseline missing: run bootstrap first')
        store.observe(sha,snapshot)
        items=store.due(int(clock()),20);result['queued']=len(items)
        if not items:return result
        verify_key(config,http)
        def check(item):
            if time.monotonic()-started>90:return False
            try:return verify_page(item,http)
            except (OSError,ValueError):return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            checked=list(zip(items,pool.map(check,items)))
        ready=[]
        for item,valid in checked:
            if valid:ready.append(item)
            else:
                store.retry(owner,item,'public version/status/robots not confirmed',None,int(clock()))
                result['deferred']+=1
        if not ready:return result
        if time.monotonic()-started>105 or read_marker(config)!=sha or not store.owns(owner,int(clock())):
            result['deferred']+=len(ready);return result
        try:
            response=submit_batch(config,[i.url for i in ready],http)
            code=response.status
            status='submitted' if code==200 else 'accepted_pending_key' if code==202 else 'blocked' if code in (400,403,422) else 'retry'
            delay=retry_after(response.headers,int(clock()))
        except (OSError,ValueError) as error:
            code=None;status='retry';delay=None
        for item in ready:
            if status=='retry':store.retry(owner,item,'IndexNow transport/server failure',code,int(clock()),retry_after=delay)
            else:store.complete(owner,item,status,code,int(clock()))
            result[status]+=1
            event(config,{'event':'notification','url':item.url,'fingerprint':item.fingerprint,'source_sha':item.source_sha,'status':status,'http_status':code})
        return result
    finally:
        store.release(owner);store.close()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['setup','verify-key','bootstrap','run','status','retry-blocked'])
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(argv);c=None
    try:
        if args.command=='setup':
            if args.config.exists():raise FileExistsError('configuration exists; reuse it')
            if not args.output_dir:raise ValueError('setup needs --output-dir')
            key,path=create_key_artifact(args.output_dir);root=args.config.parent
            c=Config(HOST,key,HOST+'/'+key+'.txt',r'D:\CorteFlow\work\raven-cf-release',r'D:\CorteFlow\work\raven-cf-release-logs\last-released-sha.txt',str(root/'state.sqlite3'),str(root/'events.jsonl'))
            root.mkdir(parents=True,exist_ok=True)
            with args.config.open('x',encoding='utf-8') as f:json.dump(asdict(c),f,indent=2)
            result={'key_file':str(path),'enabled':False}
        else:
            c=load_config(args.config)
            if args.command=='verify-key':verify_key(c,UrllibTransport());result={'key_verified':True}
            elif args.command=='run':result=run_once(c,dry_run=args.dry_run)
            else:
                if args.command=='status' and not Path(c.state_db).exists():result={'baseline_missing':True}
                else:
                    s=StateStore(Path(c.state_db),readonly=args.command=='status')
                    try:
                        if args.command=='bootstrap':
                            sha=read_marker(c);snap=read_snapshot(Path(c.repo),sha)
                            if read_marker(c)!=sha:raise ValueError('release marker changed during bootstrap')
                            owner=uuid.uuid4().hex
                            if not s.claim(owner,int(time.time())):raise ValueError('notifier busy')
                            try:s.bootstrap(sha,snap)
                            finally:s.release(owner)
                        elif args.command=='retry-blocked':s.retry_blocked(int(time.time()))
                        result=s.status()
                    finally:s.close()
        if c and args.command=='run' and not args.dry_run:event(c,{'event':'run','result':result})
        print(json.dumps(result,ensure_ascii=False));return 0
    except Exception as error:
        result={'error':type(error).__name__+': '+str(error)}
        if c:
            try:event(c,{'event':'error',**result})
            except OSError:pass
        print(json.dumps(result,ensure_ascii=False));return 1

if __name__=='__main__':raise SystemExit(main())

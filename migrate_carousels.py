"""Prepare a safe, idempotent migration from legacy carousels to one-photo posts."""
import json,glob,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'public'/'editorial'/'single-photo-migration.json'
items=[]
for p in sorted((root/'public'/'carrosseis').glob('*/manifest.json')):
 d=json.loads(p.read_text(encoding='utf-8-sig'))
 key=d.get('articleId') or p.parent.name
 photo=d.get('sourceImage') or d.get('image')
 items.append({'legacy_id':p.parent.name,'article_id':key,'old_status':d.get('status'),'legacy_published':bool(d.get('publishedToInstagram') or d.get('postId') or d.get('buffer',{}).get('postId') if isinstance(d.get('buffer'),dict) else d.get('publishedToInstagram') or d.get('postId')),'new_format':'single-photo-1080x1350','source_photo':photo,'photo_verified':False,'protected_regions_verified':False,'caption_reviewed':False,'new_image':None,'new_post_id':None,'migration_status':'NEEDS_VERIFIED_PHOTO','reason':'Legacy carousel has no validated original photograph and protected-region coordinates; do not substitute slide1 or invent an image.'})
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'schema':'raven-single-photo-migration-v1','count':len(items),'items':items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('QUEUED',len(items),'OLD_PUBLISHED',sum(x['legacy_published'] for x in items))

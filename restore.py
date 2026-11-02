"""Restore only to a NEW directory; never overwrite a live archive."""
import argparse, json, zipfile
from pathlib import Path
from backup import verify

def restore(archive,destination):
    count=verify(archive); dest=Path(destination).resolve()
    if dest.exists(): raise ValueError('Destination must not exist. Restore into a new directory.')
    with zipfile.ZipFile(archive) as z:
        names=list(json.loads(z.read('manifest.json')))
        for name in names:
            target=(dest/name).resolve()
            if not target.is_relative_to(dest) or name.startswith('/'): raise ValueError('Unsafe archive path.')
        if 'family.db' not in names: raise ValueError('Database missing.')
        dest.mkdir(parents=True)
        for name in names:
            target=dest/name; target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(name) as source,target.open('wb') as out:
                import shutil
                shutil.copyfileobj(source,out)
    return count

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('archive'); p.add_argument('destination'); args=p.parse_args()
    print(f'Restored {restore(args.archive,args.destination)} verified files. Review before changing DATA_DIR.')

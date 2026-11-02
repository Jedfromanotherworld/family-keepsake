"""Create and verify portable backups. Original upload objects are immutable."""
import argparse, hashlib, json, os, sqlite3, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

def backup(data, output):
    data=Path(data).resolve(); output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    if not (data/'family.db').is_file(): raise ValueError('No database. Run init-db first.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target=output/f'keepsake-{stamp}.zip'; manifest={}
    with tempfile.TemporaryDirectory() as temp:
        snapshot=Path(temp)/'family.db'
        with sqlite3.connect(f'file:{data / "family.db"}?mode=ro',uri=True) as source, sqlite3.connect(snapshot) as dest: source.backup(dest)
        with sqlite3.connect(snapshot) as db: rows=db.execute('SELECT id,sha256 FROM memories').fetchall()
        try:
            with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as z:
                with snapshot.open('rb') as f: manifest['family.db']=hashlib.file_digest(f,'sha256').hexdigest()
                z.write(snapshot,'family.db')
                for mid, expected in rows:
                    file=data/'uploads'/mid
                    with file.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
                    if digest!=expected: raise ValueError(f'Checksum mismatch: {mid}')
                    manifest['uploads/'+mid]=digest; z.write(file,'uploads/'+mid)
                z.writestr('manifest.json',json.dumps(manifest,indent=2))
        except BaseException:
            target.unlink(missing_ok=True); raise
    return target

def verify(path):
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read('manifest.json'))
        for name,digest in manifest.items():
            with z.open(name) as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=digest: raise ValueError(f'Corrupt backup: {name}')
    return len(manifest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--data',default=os.environ.get('DATA_DIR','data')); parser.add_argument('--output',default='backups'); parser.add_argument('--verify')
    args=parser.parse_args()
    if args.verify: print(f'Verified {verify(args.verify)} files.')
    else:
        result=backup(args.data,args.output); verify(result); print(f'Backup created and verified: {result}')
        print('Copy this archive to an encrypted off-site destination. This local file is not an off-site backup.')

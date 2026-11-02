import os, sqlite3, secrets, hashlib, time
from pathlib import Path
from datetime import timedelta, date
from functools import wraps
import click
from flask import Flask, g, request, session, jsonify, render_template, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','member')), active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS albums(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, title TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '', taken TEXT NOT NULL, album_id INTEGER REFERENCES albums(id), uploader INTEGER NOT NULL REFERENCES users(id), filename TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL, favorite INTEGER NOT NULL DEFAULT 0, deleted INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS memories_date ON memories(taken);
CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, until INTEGER NOT NULL);
PRAGMA user_version=1;
'''

def create_app(config=None):
    app = Flask(__name__)
    data = Path(os.environ.get('DATA_DIR', 'data')).resolve()
    app.config.update(DATA_DIR=data, SECRET_KEY=os.environ.get('SECRET_KEY'), MAX_CONTENT_LENGTH=260*1024*1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ONLY') == '1', PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
                      STORAGE_LIMIT_BYTES=int(os.environ.get('STORAGE_LIMIT_GB','100'))*1024**3)
    if config: app.config.update(config)
    data = Path(app.config['DATA_DIR']); data.mkdir(parents=True, exist_ok=True)
    (data/'uploads').mkdir(exist_ok=True)
    if not app.config['SECRET_KEY']:
        # A persistent local secret. Set SECRET_KEY explicitly on your production host.
        secret = data/'session.key'
        try:
            fd = os.open(secret, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f: f.write(secrets.token_hex(32))
        except FileExistsError: pass
        app.config['SECRET_KEY'] = secret.read_text()

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(data/'family.db', timeout=30)
            g.db.row_factory=sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close(_):
        if 'db' in g: g.db.close()

    @app.cli.command('init-db')
    def init_db():
        db().executescript(SCHEMA); click.echo('Database ready. Existing memories preserved.')

    @app.cli.command('create-user')
    @click.option('--name', prompt=True)
    @click.option('--email', prompt=True)
    @click.option('--admin', is_flag=True)
    @click.password_option()
    def create_user(name, email, admin, password):
        if len(password)<12: raise click.ClickException('Use at least 12 characters.')
        try:
            db().execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',
                         (name.strip(),email.strip().lower(),generate_password_hash(password),'admin' if admin else 'member'))
            db().commit(); click.echo('Account created.')
        except sqlite3.IntegrityError: raise click.ClickException('Email already exists.')

    @app.cli.command('reset-password')
    @click.option('--email', prompt=True)
    @click.password_option()
    def reset_password(email,password):
        if len(password)<12: raise click.ClickException('Use at least 12 characters.')
        cur=db().execute('UPDATE users SET password=? WHERE email=?',(generate_password_hash(password),email.lower().strip()))
        db().commit(); click.echo('Password updated.' if cur.rowcount else 'Account not found.')

    @app.before_request
    def protect():
        g.user=None
        if session.get('uid'):
            row=db().execute('SELECT id,name,email,role FROM users WHERE id=? AND active=1',(session['uid'],)).fetchone()
            if row: g.user=dict(row)
        if request.method in ('POST','PUT','PATCH','DELETE'):
            token=request.headers.get('X-CSRF-Token','')
            if not token or not secrets.compare_digest(token,session.get('csrf','')): abort(403,description='Refresh the page and try again.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' blob:; media-src 'self' blob:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        response.headers['Cache-Control']='no-store'
        if app.config['SESSION_COOKIE_SECURE']: response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def error(e): return jsonify(error='Maximum upload is 250 MB.' if e.code==413 else e.description),e.code

    def login_required(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            if not g.user: abort(401,description='Please sign in.')
            return fn(*args,**kwargs)
        return wrapped

    def admin_required():
        if g.user['role']!='admin': abort(403,description='Only an administrator can do this.')

    @app.get('/')
    def index(): return render_template('index.html')

    @app.get('/api/session')
    def who():
        if 'csrf' not in session: session['csrf']=secrets.token_hex(32)
        return jsonify(user=g.user,csrf=session['csrf'])

    @app.post('/api/login')
    def login():
        body=request.get_json() or {}; email=str(body.get('email','')).strip().lower()
        key=hashlib.sha256(email.encode()).hexdigest(); now=int(time.time())
        db().execute('DELETE FROM attempts WHERE until<?',(now,))
        db().execute('INSERT INTO attempts(key,count,until) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,now+900))
        db().commit()
        if db().execute('SELECT count FROM attempts WHERE key=?',(key,)).fetchone()[0]>10:
            abort(429,description='Too many attempts. Try again in 15 minutes.')
        row=db().execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
        if not row or not check_password_hash(row['password'],str(body.get('password',''))): abort(401,description='Email or password is incorrect.')
        db().execute('DELETE FROM attempts WHERE key=?',(key,)); db().commit()
        session.clear(); session.update(uid=row['id'],csrf=secrets.token_hex(32)); session.permanent=True
        return jsonify(ok=True)

    @app.post('/api/logout')
    def logout(): session.clear(); return jsonify(ok=True)

    @app.get('/api/library')
    @login_required
    def library():
        rows=db().execute('SELECT m.*,a.name album,u.name uploader_name FROM memories m LEFT JOIN albums a ON a.id=m.album_id JOIN users u ON u.id=m.uploader ORDER BY taken DESC,created DESC').fetchall()
        items=[dict(r) for r in rows]
        for item in items: item.pop('filename')
        return jsonify(memories=items,albums=[dict(r) for r in db().execute('SELECT * FROM albums ORDER BY name')],used=sum(r['size'] for r in rows),limit=app.config['STORAGE_LIMIT_BYTES'])

    @app.post('/api/albums')
    @login_required
    def album():
        name=str((request.get_json() or {}).get('name','')).strip()
        if not 1<=len(name)<=80: abort(400,description='Album name must be 1–80 characters.')
        try:
            cur=db().execute('INSERT INTO albums(name) VALUES(?)',(name,)); db().commit()
        except sqlite3.IntegrityError: abort(409,description='That album already exists.')
        return jsonify(id=cur.lastrowid),201

    def form_metadata():
        title=request.form.get('title','').strip(); taken=request.form.get('taken','')
        if not 1<=len(title)<=120: abort(400,description='Title must be 1–120 characters.')
        try: date.fromisoformat(taken)
        except ValueError: abort(400,description='Choose a valid memory date.')
        caption=request.form.get('caption','').strip()
        if len(caption)>2000: abort(400,description='Caption must be under 2,000 characters.')
        album=request.form.get('album_id') or None
        if album and not db().execute('SELECT id FROM albums WHERE id=?',(album,)).fetchone(): abort(400,description='Album not found.')
        return title,taken,caption,album

    @app.post('/api/memories')
    @login_required
    def upload():
        title,taken,caption,album=form_metadata()
        f=request.files.get('file')
        if not f or not f.filename: abort(400,description='Choose a photo or video.')
        head=f.stream.read(32); f.stream.seek(0)
        if head.startswith(b'\xff\xd8\xff'): mime='image/jpeg'
        elif head.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png'
        elif head[:6] in (b'GIF87a',b'GIF89a'): mime='image/gif'
        elif head[:4]==b'RIFF' and head[8:12]==b'WEBP': mime='image/webp'
        elif head[4:8]==b'ftyp' and head[8:12] in (b'isom',b'iso2',b'mp41',b'mp42',b'avc1',b'M4V ',b'qt  '): mime='video/mp4' if head[8:12]!=b'qt  ' else 'video/quicktime'
        elif head[:4]==b'\x1aE\xdf\xa3' and Path(f.filename).suffix.lower()=='.webm': mime='video/webm'
        else: abort(400,description='Use JPG, PNG, GIF, WebP, MP4, MOV or WebM. Convert HEIC photos before uploading.')
        mid=secrets.token_hex(16); target=data/'uploads'/mid
        try:
            f.save(target); size=target.stat().st_size
            if size>250*1024*1024: abort(413)
            with target.open('rb') as inp: digest=hashlib.file_digest(inp,'sha256').hexdigest()
            db().execute('BEGIN IMMEDIATE')
            used=db().execute('SELECT COALESCE(SUM(size),0) FROM memories').fetchone()[0]
            if used+size>app.config['STORAGE_LIMIT_BYTES']: abort(409,description='Storage limit reached. Ask your administrator to increase storage.')
            db().execute('INSERT INTO memories(id,title,caption,taken,album_id,uploader,filename,mime,size,sha256) VALUES(?,?,?,?,?,?,?,?,?,?)',
                         (mid,title,caption,taken,album,g.user['id'],secure_filename(f.filename) or 'memory',mime,size,digest))
            db().commit()
        except BaseException:
            db().rollback(); target.unlink(missing_ok=True); raise
        return jsonify(id=mid),201

    def memory(mid):
        row=db().execute('SELECT * FROM memories WHERE id=?',(mid,)).fetchone()
        if not row: abort(404,description='Memory not found.')
        return row

    @app.get('/media/<mid>')
    @login_required
    def media(mid):
        row=memory(mid)
        if row['deleted']: abort(404,description='Restore this memory to view it.')
        return send_file(data/'uploads'/row['id'],mimetype=row['mime'],as_attachment=request.args.get('download')=='1',download_name=row['filename'],conditional=True)

    @app.patch('/api/memories/<mid>')
    @login_required
    def edit(mid):
        row=memory(mid); body=request.get_json() or {}
        if set(body)=={'favorite'}:
            db().execute('UPDATE memories SET favorite=? WHERE id=?',(int(bool(body['favorite'])),mid))
        elif set(body)=={'deleted'}:
            if g.user['id']!=row['uploader']: admin_required()
            db().execute('UPDATE memories SET deleted=? WHERE id=?',(int(bool(body['deleted'])),mid))
        else: abort(400,description='Unsupported change.')
        db().commit(); return jsonify(ok=True)

    @app.get('/api/members')
    @login_required
    def members():
        return jsonify(members=[dict(r) for r in db().execute('SELECT id,name,role FROM users WHERE active=1 ORDER BY name')])

    @app.post('/api/members')
    @login_required
    def add_member():
        admin_required(); body=request.get_json() or {}
        name=str(body.get('name','')).strip(); email=str(body.get('email','')).strip().lower(); password=str(body.get('password',''))
        if not 1<=len(name)<=80 or '@' not in email or len(email)>254 or len(password)<12: abort(400,description='Enter a name, email, and password of at least 12 characters.')
        try:
            db().execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',(name,email,generate_password_hash(password),'member')); db().commit()
        except sqlite3.IntegrityError: abort(409,description='Email already exists.')
        return jsonify(ok=True),201
    return app

app=create_app()
if __name__=='__main__': app.run(host='127.0.0.1',port=5000)

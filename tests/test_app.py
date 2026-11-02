import io, tempfile, unittest, sqlite3, base64
from pathlib import Path
from app import create_app, SCHEMA
from werkzeug.security import generate_password_hash
from backup import backup, verify
from restore import restore
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1sAAAAASUVORK5CYII=')
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.data=Path(self.temp.name)/'data'
        self.app=create_app({'TESTING':True,'DATA_DIR':self.data,'SECRET_KEY':'test-only-secret'})
        with sqlite3.connect(self.data/'family.db') as db:
            db.executescript(SCHEMA)
            for name,role in [('Owner','admin'),('Member','member')]: db.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',(name,name.lower()+'@test.com',generate_password_hash('test-password-123'),role))
        self.c=self.app.test_client(); self.csrf=self.c.get('/api/session').json['csrf']
    def tearDown(self): self.temp.cleanup()
    def post(self,url,body): return self.c.post(url,json=body,headers={'X-CSRF-Token':self.csrf})
    def login(self,name='owner'):
        result=self.post('/api/login',{'email':name+'@test.com','password':'test-password-123'})
        self.assertEqual(result.status_code,200); self.csrf=self.c.get('/api/session').json['csrf']
    def upload(self,content=PNG,filename='family.png'):
        return self.c.post('/api/memories',data={'file':(io.BytesIO(content),filename),'title':'Family day','taken':'2026-11-02','caption':'Hello'},headers={'X-CSRF-Token':self.csrf})
    def patch(self,mid,body):return self.c.patch('/api/memories/'+mid,json=body,headers={'X-CSRF-Token':self.csrf})
    def test_private_endpoints(self):
        for url in ['/api/library','/api/members','/media/nope']: self.assertEqual(self.c.get(url).status_code,401)
    def test_csrf_required(self): self.assertEqual(self.c.post('/api/login',json={}).status_code,403)
    def test_login_and_logout(self):
        self.login(); self.assertEqual(self.c.get('/api/session').json['user']['role'],'admin'); self.post('/api/logout',{}); self.assertEqual(self.c.get('/api/library').status_code,401)
    def test_bad_password_and_throttle(self):
        for _ in range(10): self.assertEqual(self.post('/api/login',{'email':'owner@test.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('/api/login',{'email':'owner@test.com','password':'wrong'}).status_code,429)
    def test_upload_download_and_range(self):
        self.login(); r=self.upload(); self.assertEqual(r.status_code,201); mid=r.json['id']
        response=self.c.get('/media/'+mid); self.assertEqual(response.data,PNG); response.close()
        response=self.c.get('/media/'+mid,headers={'Range':'bytes=0-7'}); self.assertEqual(response.status_code,206); self.assertEqual(response.data,PNG[:8]); response.close()
        response=self.c.get('/media/'+mid+'?download=1'); self.assertIn('attachment',response.headers['Content-Disposition']); response.close()
    def test_reject_html(self):
        self.login(); self.assertEqual(self.upload(b'<script>alert(1)</script>','bad.jpg').status_code,400)
    def test_album_favorite_trash_restore(self):
        self.login(); self.assertEqual(self.post('/api/albums',{'name':'Birthdays'}).status_code,201)
        self.assertEqual(self.post('/api/albums',{'name':'Birthdays'}).status_code,409)
        mid=self.upload().json['id']; self.assertEqual(self.patch(mid,{'favorite':True}).status_code,200)
        self.patch(mid,{'deleted':True}); self.assertEqual(self.c.get('/media/'+mid).status_code,404)
        self.patch(mid,{'deleted':False}); r=self.c.get('/media/'+mid); self.assertEqual(r.status_code,200); r.close()
    def test_member_cannot_remove_others_or_create_users(self):
        self.login(); mid=self.upload().json['id']; self.post('/api/logout',{}); self.csrf=self.c.get('/api/session').json['csrf']; self.login('member')
        self.assertEqual(self.patch(mid,{'deleted':True}).status_code,403)
        self.assertEqual(self.post('/api/members',{'name':'New','email':'new@test.com','password':'another-password'}).status_code,403)
    def test_admin_create_member(self):
        self.login(); body={'name':'New','email':'new@test.com','password':'another-password'}
        self.assertEqual(self.post('/api/members',body).status_code,201); self.assertEqual(self.post('/api/members',body).status_code,409)
    def test_quota_cleans_failed_file(self):
        self.login(); self.app.config['STORAGE_LIMIT_BYTES']=1; self.assertEqual(self.upload().status_code,409)
        self.assertEqual(list((self.data/'uploads').iterdir()),[])
    def test_backup_restore(self):
        self.login(); mid=self.upload().json['id']; z=backup(self.data,Path(self.temp.name)/'backups'); self.assertEqual(verify(z),2)
        dest=Path(self.temp.name)/'restored'; restore(z,dest); self.assertEqual((dest/'uploads'/mid).read_bytes(),PNG)
        with self.assertRaises(ValueError):restore(z,dest)
    def test_restart_persistence(self):
        self.login(); self.upload(); other=create_app({'TESTING':True,'DATA_DIR':self.data,'SECRET_KEY':'different'}).test_client()
        with sqlite3.connect(self.data/'family.db') as db:self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0],1)
    def test_headers(self):
        response=self.c.get('/'); self.assertEqual(response.status_code,200); self.assertEqual(response.headers['X-Frame-Options'],'DENY'); self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
if __name__=='__main__':unittest.main()

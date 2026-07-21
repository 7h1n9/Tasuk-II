from flask import Flask, request, jsonify, make_response
import os, secrets, hashlib, html, re

app=Flask(__name__)
CH=os.getenv('CHALLENGE_ID','core-a04'); FLAG=os.getenv('INSTANCE_FLAG','flag{missing}')
SECRET=os.getenv('VARIANT_SEED','0'); users={'alice':'alice-pass','auditor':'audit-pass','admin':'admin-pass'}
sessions={}; records=[]; points={'alice':100}

def token(user,role='user'):
    raw=f'{user}:{role}:{SECRET}'.encode(); return raw.hex()
def current():
    t=request.cookies.get('session') or request.headers.get('Authorization','').removeprefix('Bearer ')
    for u in users:
        if t in (token(u),token(u,'admin'),token(u,'auditor')): return u
    return None
@app.get('/health')
def health(): return jsonify(status='ok', challenge=CH)
@app.get('/')
def index(): return jsonify(title=CH, description='Authorized security validation task', objective='Find the hidden flag', hint='Observe how inputs move through the workflow', flag_format='flag{...}')
@app.post('/login')
def login():
    d=request.get_json(silent=True) or request.form
    u=d.get('username',''); p=d.get('password','')
    if users.get(u)!=p:return jsonify(error='invalid credentials'),401
    r=make_response(jsonify(ok=True,user=u)); r.set_cookie('session',token(u)); return r

@app.route('/recover',methods=['GET','POST'])
def recover():
    if request.method=='GET': return jsonify(fields=['account','verification_code','new_password'])
    d=request.get_json(silent=True) or request.form; account=d.get('account','alice'); code=d.get('verification_code','')
    if account=='admin' and code==hashlib.sha256((SECRET+'admin').encode()).hexdigest()[:8]: users['admin']=d.get('new_password','recovered'); return jsonify(ok=True,transition='admin')
    return jsonify(ok=True,message='recovery request accepted')

@app.post('/preview')
def preview():
    d=request.get_json(silent=True) or request.form; text=str(d.get('template',d.get('content','')))
    text=text.replace('{{name}}','Employee').replace('{{department}}','Operations')
    if '{{flag}}' in text and ('config' in text or 'settings' in text): text=text.replace('{{flag}}',FLAG)
    if CH=='core-c04' and ('config' in text or 'settings' in text): text=text.replace('{{config}}',FLAG).replace('{{settings}}',FLAG)
    elif CH=='core-c04' and re.search(r'\{\{\s*[^}]+\}\}',text): text=html.escape(text)
    return jsonify(rendered=text)

@app.route('/audit',methods=['GET','POST'])
def audit():
    if request.method=='POST':
        d=request.get_json(silent=True) or request.form; records.append(str(d.get('display_name',''))); return jsonify(ok=True)
    q=request.args.get('q','')
    if CH=='core-b04' and q and any(x in q.lower() for x in ['select','union','--']): return jsonify(results=[{'event':x} for x in records]+[{'event':FLAG}])
    return jsonify(results=[{'event':x} for x in records])

@app.route('/check',methods=['GET','POST'])
def check():
    d=request.get_json(silent=True) or request.form; target=str(d.get('target',d.get('url','')))
    if CH=='core-c05' and (';' in target or '|' in target or '$(' in target): return jsonify(output=FLAG)
    if CH=='core-d02' and ('redirect' in target or target.endswith('/final')): return jsonify(content=FLAG)
    return jsonify(status='reachable',target=target)

@app.route('/assets',methods=['GET','POST'])
def assets():
    if request.method=='POST':
        d=request.get_json(silent=True) or request.form; records.append(str(d)); return jsonify(ok=True,location='/assets/preview/1')
    if CH=='core-d06' and request.args.get('preview')=='1': return jsonify(content=FLAG)
    return jsonify(items=records)

@app.post('/redeem')
def redeem():
    u=current() or 'alice'; n=int((request.get_json(silent=True) or {}).get('count',1)); points[u]=points.get(u,100)-n*10
    if CH=='core-d03' and n>=5:return jsonify(ok=True,item='premium',flag=FLAG)
    return jsonify(ok=True,item='standard',points=points[u])

@app.get('/projects/<path:pid>')
def project(pid):
    if CH=='core-d05' and pid in ('admin','999','secret'): return jsonify(project=pid,flag=FLAG)
    return jsonify(project=pid,access='limited')

@app.get('/advanced')
def advanced(): return jsonify(user=current(), stages=['authentication','discovery','transition','protected_access'])

@app.get('/account')
def account(): return jsonify(account=current(), flag=FLAG if current()=='admin' else None)

@app.get('/review')
def review(): return jsonify(status='approved', flag=FLAG if CH=='core-a05' and current() in ('auditor','admin') else None)

@app.get('/search')
def search(): return jsonify(items=['audit record'], privileged=FLAG if CH=='core-b05' and request.args.get('scope')=='all' else None)

@app.get('/logs')
def logs(): return jsonify(entries=['application event'], export=FLAG if CH=='core-c02' and request.args.get('format')=='full' else None)

@app.get('/profile/<path:oid>')
def profile(oid): return jsonify(profile=oid, flag=FLAG if CH=='core-a01' and oid in ('admin','999','3') else None)

@app.post('/inventory')
def inventory():
    d=request.get_json(silent=True) or {}; return jsonify(items=['laptop','printer'], metadata=FLAG if CH=='core-b01' and d.get('scope')=='all' else None)

@app.get('/report')
def report(): return jsonify(report='summary', export=FLAG if CH=='core-b02' and request.args.get('format')=='full' else None)

@app.get('/document')
def document(): return jsonify(document='preview', attachment=FLAG if CH=='core-c01' and request.args.get('preview')=='full' else None)

@app.get('/fetch')
def fetch(): return jsonify(target=request.args.get('target',''), content=FLAG if CH=='core-d01' and 'final' in request.args.get('target','') else 'ok')

@app.get('/orders')
def orders(): return jsonify(order='approved', detail=FLAG if CH=='core-a02' and request.args.get('order_id') in ('999','3') else 'limited')

@app.get('/portal')
def portal(): return jsonify(user=current(), admin_data=FLAG if CH=='core-a03' and current()=='admin' else None)

@app.get('/assets/list')
def asset_list(): return jsonify(items=['server','router'], secret=FLAG if CH=='core-b03' and request.args.get('sort')=='secret' else None)

@app.get('/upload')
def upload(): return jsonify(status='processed', preview=FLAG if CH=='core-c03' and request.args.get('preview')=='1' else None)

@app.post('/graphql')
def graphql():
    d=request.get_json(silent=True) or {}; q=str(d.get('query','')); return jsonify(data={'viewer':'ok','sensitive':FLAG if CH=='core-d04' and 'sensitive' in q else None})

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')))

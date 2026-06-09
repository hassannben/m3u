from flask import Flask, Response, render_template_string, request, redirect, url_for, jsonify, session as flask_session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

app = Flask(__name__)
# تغيير مفتاح التشفير لجعل الجلسة أكثر استقراراً
app.secret_key = "iptv_secret_secure_key_12345"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

http_session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
http_session.mount('http://', adapter)
http_session.mount('https://', adapter)
http_session.headers.update(HEADERS)

def safe_fetch(url):
    try:
        response = http_session.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

# [واجهات الـ HTML كما هي في طلبك السابق...]
# (يمكنك وضع LOGIN_INTERFACE و PLAYER_INTERFACE هنا كما أرسلتهما سابقاً)

@app.route('/')
def home():
    return render_template_string(LOGIN_INTERFACE)

@app.route('/login', methods=['POST'])
def login():
    flask_session['host'] = request.form.get('host', '').strip().rstrip('/')
    flask_session['username'] = request.form.get('username', '').strip()
    flask_session['password'] = request.form.get('password', '').strip()
    return redirect(url_for('player'))

@app.route('/player')
def player():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')
    if not host: return redirect(url_for('home'))
    
    base_api = f"{host}/player_api.php?username={username}&password={password}"
    packaged_data = {
        "live_cats": safe_fetch(f"{base_api}&action=get_live_categories") or [],
        "vod_cats": safe_fetch(f"{base_api}&action=get_vod_categories") or []
    }
    return render_template_string(PLAYER_INTERFACE, data=packaged_data)

@app.route('/get_streams')
def get_streams():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')
    stream_type = request.args.get('type', 'live')
    category_id = request.args.get('category_id')

    base_api = f"{host}/player_api.php?username={username}&password={password}"
    action = "get_live_streams" if stream_type == "live" else "get_vod_streams"
    streams = safe_fetch(f"{base_api}&action={action}&category_id={category_id}")
    
    parsed_results = []
    if isinstance(streams, list):
        for ch in streams:
            s_id = ch.get("stream_id")
            token = ch.get("token", "")
            ext = ch.get("container_extension", "m3u8")
            if stream_type == 'live':
                proxy_url = f"/proxy/live/{s_id}.{ext}?token={token}"
            else:
                proxy_url = f"/proxy/movie/{s_id}.{ext}"
            
            parsed_results.append({
                "name": ch.get("name"),
                "proxy_url": proxy_url
            })
    return jsonify(parsed_results)

@app.route('/proxy/<path:stream_path>')
def proxy_stream(stream_path):
    host = flask_session.get('host')
    target_url = f"{host}/{stream_path}"
    if request.query_string: target_url += f"?{request.query_string.decode('utf-8')}"
    
    try:
        # إضافة تصحيح للأخطاء (Debug)
        req = requests.get(target_url, headers=HEADERS, stream=True, timeout=15)
        print(f"DEBUG: Requesting {target_url} | Status: {req.status_code}")
        
        if '.m3u8' in stream_path:
            content = req.text
            fixed_content = re.sub(r'([^\s\n\r]+\.ts)', lambda m: f"/proxy/{stream_path.rsplit('/', 1)[0]}/{m.group(1)}", content)
            return Response(fixed_content, content_type='application/x-mpegURL')
        
        return Response(req.iter_content(chunk_size=1024*512), 
                        content_type=req.headers.get('Content-Type', 'video/mp2t'),
                        status=req.status_code)
    except Exception as e:
        print(f"PROXY ERROR: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

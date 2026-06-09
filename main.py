from flask import Flask, Response, render_template_string, request, redirect, url_for, jsonify, session as flask_session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

app = Flask(__name__)
app.secret_key = "iptv_secret_secure_key_12345"

# --- 1. تعريف واجهات الـ HTML (يجب أن تكون في الأعلى) ---
LOGIN_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>IPTV PORTAL PRO</title>
    <style>body{background:#0b0914; color:#fff; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;}</style>
</head>
<body>
    <form method="POST" action="/login" style="background:#161226; padding:30px; border-radius:15px;">
        <h2>دخول IPTV</h2>
        <input type="url" name="host" placeholder="Host URL" required style="width:100%; margin-bottom:10px;"><br>
        <input type="text" name="username" placeholder="Username" required style="width:100%; margin-bottom:10px;"><br>
        <input type="password" name="password" placeholder="Password" required style="width:100%; margin-bottom:10px;"><br>
        <button type="submit" style="width:100%; padding:10px; background:#00f2fe; border:none; cursor:pointer;">دخول</button>
    </form>
</body>
</html>
'''

PLAYER_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><title>Player</title></head>
<body><h1>تم الدخول بنجاح!</h1></body>
</html>
'''

# --- 2. الإعدادات ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
}

http_session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
http_session.mount('http://', adapter)
http_session.mount('https://', adapter)

def safe_fetch(url):
    try:
        response = http_session.get(url, timeout=15, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Fetch Error: {e}")
    return None

# --- 3. المسارات (Routes) ---
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
    if 'host' not in flask_session: return redirect(url_for('home'))
    return render_template_string(PLAYER_INTERFACE)

@app.route('/proxy/<path:stream_path>')
def proxy_stream(stream_path):
    host = flask_session.get('host')
    target_url = f"{host}/{stream_path}"
    if request.query_string: target_url += f"?{request.query_string.decode('utf-8')}"
    
    try:
        req = requests.get(target_url, headers=HEADERS, stream=True, timeout=15)
        return Response(req.iter_content(chunk_size=1024*512), 
                        content_type=req.headers.get('Content-Type', 'video/mp2t'),
                        status=req.status_code)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

from flask import Flask, Response, render_template_string, request, redirect, url_for, session as flask_session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
app.secret_key = "iptv_secret_secure_key_12345"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# إعداد جلسة اتصالات محسنة لمعالجة التدفقات الكبيرة وعمليات الـ Buffering عبر البروكسي
http_session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
http_session.mount('http://', adapter)
http_session.mount('https://', adapter)
http_session.headers.update(HEADERS)

def safe_fetch(url):
    try:
        response = http_session.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# -------------------------------------------------------------
# 1. واجهة تسجيل الدخول (Login Interface)
# -------------------------------------------------------------
LOGIN_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV Portal Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Tajawal', sans-serif; background: linear-gradient(135deg, #09090e 0%, #150f24 100%); color: #fff; min-height: 100vh; margin: 0; display: flex; align-items: center; justify-content: center; padding: 20px; box-sizing: border-box; }
        .card { background: rgba(22, 17, 39, 0.7); backdrop-filter: blur(20px); width: 100%; max-width: 440px; border-radius: 24px; padding: 40px; border: 1px solid rgba(255,255,255,0.06); box-shadow: 0 20px 50px rgba(0,0,0,0.5); text-align: center; }
        h1 { margin: 0 0 10px 0; background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 26px; }
        p.desc { color: #8a8594; font-size: 14px; margin-bottom: 30px; }
        .form-group { text-align: right; margin-bottom: 20px; }
        label { display: block; font-size: 13px; color: #b1a9bc; margin-bottom: 8px; }
        input { width: 100%; padding: 14px; background: rgba(10, 7, 20, 0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; color: #fff; font-size: 15px; box-sizing: border-box; }
        .btn-group { display: flex; gap: 10px; margin-top: 25px; }
        .btn { flex: 1; padding: 15px; border: none; border-radius: 12px; font-size: 15px; font-weight: bold; cursor: pointer; }
        .btn-primary { background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%); color: #09090e; }
        .btn-secondary { background: rgba(255,255,255,0.06); color: #fff; border: 1px solid rgba(255,255,255,0.06); }
        .loading { display: none; margin-top: 20px; color: #00f2fe; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>IPTV PORTAL PRO</h1>
        <p class="desc">ادخل بيانات سيرفر Xtream لتشغيل القنوات السينمائية مباشرة</p>
        <form method="POST" action="/login">
            <div class="form-group">
                <label>رابط السيرفر (Host URL)</label>
                <input type="url" name="host" placeholder="http://example.com:8080" required autocomplete="off">
            </div>
            <div class="form-group">
                <label>اسم المستخدم (Username)</label>
                <input type="text" name="username" placeholder="Username" required autocomplete="off">
            </div>
            <div class="form-group">
                <label>كلمة المرور (Password)</label>
                <input type="password" name="password" placeholder="Password" required autocomplete="off">
            </div>
            <div class="btn-group">
                <button type="submit" onclick="setMode('play')" class="btn btn-primary">🖥️ دخول للمشغل</button>
                <button type="submit" onclick="setMode('download')" class="btn btn-secondary">📥 تحميل M3U</button>
            </div>
            <input type="hidden" name="mode" id="formMode" value="play">
        </form>
        <div class="loading" id="loadStatus">جاري الاتصال بالسيرفر وجلب القنوات...</div>
    </div>
    <script>
        function setMode(mode) {
            document.getElementById('formMode').value = mode;
            document.getElementById('loadStatus').style.display = 'block';
        }
    </script>
</body>
</html>
'''

# -------------------------------------------------------------
# 2. واجهة مشغل الـ IPTV والسينما (Player Interface)
# -------------------------------------------------------------
PLAYER_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المشغل السينمائي المباشر</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Tajawal', sans-serif; background: #0b0914; color: #fff; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
        header { background: #141124; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); }
        header h1 { margin: 0; font-size: 20px; color: #00f2fe; }
        .logout-btn { background: rgba(255, 59, 48, 0.2); color: #ff3b30; border: 1px solid rgba(255, 59, 48, 0.4); padding: 8px 16px; border-radius: 8px; cursor: pointer; text-decoration: none; font-size: 13px; }
        .main-layout { display: flex; flex: 1; overflow: hidden; }
        .video-section { flex: 2; background: #000; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; }
        .video-container { width: 100%; height: 100%; max-height: 85vh; display: flex; justify-content: center; align-items: center; }
        video { width: 100%; height: 100%; max-height: 100%; background: #000; outline: none; }
        .video-title { position: absolute; top: 15px; left: 20px; background: rgba(0,0,0,0.8); padding: 8px 15px; border-radius: 6px; font-size: 14px; z-index: 10; color: #00f2fe; border: 1px solid rgba(255,255,255,0.05); }
        .content-sidebar { flex: 1; background: #110e1c; display: flex; flex-direction: column; overflow-y: auto; max-width: 400px; width: 100%; }
        .tabs { display: flex; background: #161226; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; font-weight: bold; color: #8a8594; }
        .tab.active { color: #00f2fe; background: #110e1c; border-bottom: 2px solid #00f2fe; }
        .items-list { padding: 10px; overflow-y: auto; flex: 1; }
        .item-row { display: flex; align-items: center; padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.02); cursor: pointer; border-radius: 8px; margin-bottom: 4px; transition: 0.2s; }
        .item-row:hover { background: rgba(0, 242, 254, 0.08); }
        .item-row img { width: 36px; height: 36px; object-fit: contain; margin-left: 12px; }
        .item-details { text-align: right; }
        .item-name { font-size: 14px; font-weight: 600; color: #eaeaea; }
        .item-group { font-size: 11px; color: #6f6a7a; margin-top: 2px; }
        @media (max-width: 768px) { .main-layout { flex-direction: column; } .content-sidebar { max-width: 100%; } .video-section { height: 40vh; flex: none; } }
    </style>
</head>
<body>

    <header>
        <h1>IPTV LIVE CINEMA PLAYER</h1>
        <a href="/logout" class="logout-btn">خروج وتغيير السيرفر</a>
    </header>

    <div class="main-layout">
        <div class="video-section">
            <div class="video-title" id="currentPlayingTitle">اختر قناة أو فيلماً لبدء العرض المباشر</div>
            <div class="video-container">
                <video id="my-video" controls autoplay playsinline></video>
            </div>
        </div>

        <div class="content-sidebar">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('live')">📺 قنوات مباشرة</div>
                <div class="tab" onclick="switchTab('vod')">🎬 أفلام سينما</div>
            </div>

            <div id="liveList" class="items-list">
                {% for item in data.live %}
                    <div class="item-row" onclick="playVideo('{{ item.proxy_url }}', '{{ item.name }}', 'live')">
                        <img src="https://cdn-icons-png.flaticon.com/512/716/716429.png">
                        <div class="item-details">
                            <div class="item-name">{{ item.name }}</div>
                            <div class="item-group">{{ item.cat }}</div>
                        </div>
                    </div>
                {% endfor %}
            </div>

            <div id="vodList" class="items-list" style="display: none;">
                {% for item in data.movies %}
                    <div class="item-row" onclick="playVideo('{{ item.proxy_url }}', '{{ item.name }}', 'vod')">
                        <img src="https://cdn-icons-png.flaticon.com/512/4221/4221359.png">
                        <div class="item-details">
                            <div class="item-name">{{ item.name }}</div>
                            <div class="item-group">{{ item.cat }}</div>
                        </div>
                    </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        var videoElement = document.getElementById('my-video');
        var hls = null;

        function switchTab(type) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            if (type === 'live') {
                document.querySelectorAll('.tab')[0].classList.add('active');
                document.getElementById('liveList').style.display = 'block';
                document.getElementById('vodList').style.display = 'none';
            } else {
                document.querySelectorAll('.tab')[1].classList.add('active');
                document.getElementById('liveList').style.display = 'none';
                document.getElementById('vodList').style.display = 'block';
            }
        }

        function playVideo(proxyUrl, name, type) {
            document.getElementById('currentPlayingTitle').innerText = "يعرض الآن: " + name;
            
            if (hls) {
                hls.destroy();
                hls = null;
            }

            if (type === 'live') {
                if (Hls.isSupported()) {
                    hls = new Hls({
                        enableWorker: true,
                        lowLatencyMode: true,
                        maxBufferLength: 8
                    });
                    hls.loadSource(proxyUrl);
                    hls.attachMedia(videoElement);
                    hls.on(Hls.Events.MANIFEST_PARSED, function() {
                        videoElement.play().catch(e => console.log(e));
                    });
                    hls.on(Hls.Events.ERROR, function(event, data) {
                        if (data.fatal) {
                            videoElement.src = proxyUrl;
                            videoElement.play().catch(e => console.log(e));
                        }
                    });
                } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
                    videoElement.src = proxyUrl;
                    videoElement.play();
                } else {
                    videoElement.src = proxyUrl;
                    videoElement.play().catch(e => console.log(e));
                }
            } else {
                videoElement.src = proxyUrl;
                videoElement.play().catch(err => console.log("خطأ في تشغيل الفيلم: ", err));
            }
        }
    </script>
</body>
</html>
'''

# -------------------------------------------------------------
# 3. توجيهات والتحكم الخلفي بـ Flask (Backend Routes)
# -------------------------------------------------------------
@app.route('/')
def home():
    return render_template_string(LOGIN_INTERFACE)

@app.route('/login', methods=['POST'])
def login():
    flask_session['host'] = request.form.get('host', '').strip().rstrip('/')
    flask_session['username'] = request.form.get('username', '').strip()
    flask_session['password'] = request.form.get('password', '').strip()
    
    if request.form.get('mode') == 'download':
        return redirect(url_for('download_m3u'))
    return redirect(url_for('player'))

@app.route('/player')
def player():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')

    if not host or not username or not password:
        return redirect(url_for('home'))

    base_api = f"{host}/player_api.php?username={username}&password={password}"
    packaged_data = {"live": [], "movies": []}

    live_cats = safe_fetch(f"{base_api}&action=get_live_categories")
    if isinstance(live_cats, list):
        for cat in live_cats[:4]: 
            streams = safe_fetch(f"{base_api}&action=get_live_streams&category_id={cat.get('category_id')}")
            if isinstance(streams, list):
                for ch in streams[:8]:
                    if ch.get("stream_id"):
                        packaged_data["live"].append({
                            "name": ch.get("name"),
                            "cat": cat.get("category_name"),
                            "proxy_url": f"/proxy?type=live&id={ch.get('stream_id')}"
                        })

    vod_cats = safe_fetch(f"{base_api}&action=get_vod_categories")
    if isinstance(vod_cats, list):
        for cat in vod_cats[:4]: 
            streams = safe_fetch(f"{base_api}&action=get_vod_streams&category_id={cat.get('category_id')}")
            if isinstance(streams, list):
                for movie in streams[:8]:
                    if movie.get("stream_id"):
                        ext = movie.get("container_extension", "mp4")
                        packaged_data["movies"].append({
                            "name": movie.get("name"),
                            "cat": cat.get("category_name"),
                            "proxy_url": f"/proxy?type=movie&id={movie.get('stream_id')}&ext={ext}"
                        })

    return render_template_string(PLAYER_INTERFACE, data=packaged_data)

# -------------------------------------------------------------
# 4. محرك البروكسي (Proxy Engine) تحويل تلقائي إلى m3u8
# -------------------------------------------------------------
@app.route('/proxy')
def proxy_stream():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')
    
    if not host:
        return "غير مصرح لك بالوصول", 403

    stream_type = request.args.get('type') 
    stream_id = request.args.get('id')
    ext = request.args.get('ext', 'ts' if stream_type == 'live' else 'mp4')

    if stream_type == 'live' and ext == 'ts':
        ext = 'm3u8'

    target_url = f"{host}/{stream_type}/{username}/{password}/{stream_id}.{ext}"

    try:
        req = http_session.get(target_url, stream=True, timeout=15)
        
        def stream_video():
            for chunk in req.iter_content(chunk_size=1024*64): 
                if chunk:
                    yield chunk

        return Response(stream_video(), content_type=req.headers.get('Content-Type', 'application/vnd.apple.mpegurl'))
    except Exception as e:
        return f"فشل البروكسي في سحب دفق الميديا: {e}", 500

# -------------------------------------------------------------
# 5. قائمة قنوات M3U
# -------------------------------------------------------------
@app.route('/download')
def download_m3u():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')
    if not host: return redirect(url_for('home'))

    def generate():
        yield "#EXTM3U\n"
        base_api = f"{host}/player_api.php?username={username}&password={password}"
        for action, block_type in [("get_live_categories", "live"), ("get_vod_categories", "movie")]:
            cats = safe_fetch(f"{base_api}&action={action}")
            if isinstance(cats, list):
                for cat in cats:
                    streams = safe_fetch(f"{base_api}&action=get_live_streams&category_id={cat.get('category_id')}" if block_type == "live" else f"{base_api}&action=get_vod_streams&category_id={cat.get('category_id')}")
                    if isinstance(streams, list):
                        for item in streams:
                            s_id = item.get("stream_id")
                            if s_id:
                                ext = "m3u8" if block_type == "live" else item.get("container_extension", "mp4")
                                yield f'#EXTINF:-1 group-title="{cat.get("category_name")}",{item.get("name")}\n'
                                yield f"{host}/{block_type}/{username}/{password}/{s_id}.{ext}\n"

    return Response(generate(), mimetype='text/plain', headers={"Content-Disposition": "attachment;filename=playlist.m3u"})

@app.route('/logout')
def logout():
    flask_session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, Response, render_template_string, request, redirect, url_for, jsonify, session as flask_session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

app = Flask(__name__)
app.secret_key = "iptv_secret_secure_key_12345"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Encoding": "identity" # نطلب من السيرفر عدم إرسال بيانات مضغوطة لتسهيل القراءة والنظام النصي
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
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght=400;700&display=swap" rel="stylesheet">
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
        <p class="desc">ادخل بيانات سيرفر Xtream لتشغيل القنوات والسينما فوراً</p>
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
        <div class="loading" id="loadStatus">جاري الاتصال السريع بالسيرفر...</div>
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
# 2. واجهة المشغل (Player Interface)
# -------------------------------------------------------------
PLAYER_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المشغل السينمائي المباشر</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght=400;700&display=swap" rel="stylesheet">
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
        .content-sidebar { flex: 1; background: #110e1c; display: flex; flex-direction: column; overflow-y: auto; max-width: 400px; width: 100%; border-left: 1px solid rgba(255,255,255,0.05); }
        .tabs { display: flex; background: #161226; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; font-weight: bold; color: #8a8594; }
        .tab.active { color: #00f2fe; background: #110e1c; border-bottom: 2px solid #00f2fe; }
        
        .list-container { display: flex; flex-direction: column; flex: 1; overflow-y: auto; padding: 10px; }
        .cat-row { background: rgba(255,255,255,0.03); padding: 12px; margin-bottom: 6px; border-radius: 8px; cursor: pointer; font-weight: bold; border: 1px solid rgba(255,255,255,0.05); transition: 0.2s; text-align: right;}
        .cat-row:hover { background: rgba(0, 242, 254, 0.1); color: #00f2fe; }
        
        .back-btn { background: #161226; padding: 10px; text-align: center; cursor: pointer; color: #00f2fe; font-weight: bold; margin-bottom: 10px; border-radius: 8px; border: 1px solid rgba(0, 242, 254, 0.2); display: none; }
        .items-list { display: flex; flex-direction: column; }
        .item-row { display: flex; align-items: center; padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.02); cursor: pointer; border-radius: 8px; margin-bottom: 4px; transition: 0.2s; text-align: right;}
        .item-row:hover { background: rgba(0, 242, 254, 0.08); }
        .item-row img { width: 30px; height: 30px; object-fit: contain; margin-left: 12px; }
        .item-details { flex: 1; }
        .item-name { font-size: 14px; font-weight: 600; color: #eaeaea; }
        
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
            <div class="video-title" id="currentPlayingTitle">اختر فئة ثم قناة لبدء البث المباشر</div>
            <div class="video-container">
                <video id="my-video" controls autoplay playsinline></video>
            </div>
        </div>

        <div class="content-sidebar">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('live')">📺 القنوات المباشرة</div>
                <div class="tab" onclick="switchTab('vod')">🎬 أفلام السينما</div>
            </div>

            <div class="list-container">
                <div id="backButton" class="back-btn" onclick="showCategories()">🔙 العودة لقائمة الفئات الرئيسيّة</div>
                <div id="categoriesContainer"></div>
                <div id="itemsContainer" class="items-list"></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        var videoElement = document.getElementById('my-video');
        var hls = null;
        var currentTab = 'live';
        
        var liveCategories = {{ data.live_cats|tojson }};
        var vodCategories = {{ data.vod_cats|tojson }};

        function switchTab(type) {
            currentTab = type;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            if (type === 'live') {
                document.querySelectorAll('.tab')[0].classList.add('active');
            } else {
                document.querySelectorAll('.tab')[1].classList.add('active');
            }
            showCategories();
        }

        function showCategories() {
            document.getElementById('backButton').style.display = 'none';
            document.getElementById('itemsContainer').innerHTML = '';
            var container = document.getElementById('categoriesContainer');
            container.innerHTML = '';
            container.style.display = 'block';

            var targetCats = (currentTab === 'live') ? liveCategories : vodCategories;
            
            if(!targetCats || targetCats.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:20px; color:#8a8594;">⚠️ لا توجد فئات متاحة أو فشل الاتصال</div>';
                return;
            }

            targetCats.forEach(cat => {
                var div = document.createElement('div');
                div.className = 'cat-row';
                div.innerText = cat.category_name;
                div.onclick = function() { loadCategoryItems(cat.category_id); };
                container.appendChild(div);
            });
        }

        function loadCategoryItems(catId) {
            var catContainer = document.getElementById('categoriesContainer');
            var itemsContainer = document.getElementById('itemsContainer');
            var backBtn = document.getElementById('backButton');
            
            catContainer.style.display = 'none';
            backBtn.style.display = 'block';
            itemsContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#00f2fe;">جاري تحميل المحتوى من السيرفر...</div>';

            fetch('/get_streams?type=' + currentTab + '&category_id=' + catId)
                .then(res => res.json())
                .then(data => {
                    itemsContainer.innerHTML = '';
                    if(data.length === 0) {
                        itemsContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#8a8594;">الفئة فارغة أو لا تحتوي على دفق متاح</div>';
                        return;
                    }
                    data.forEach(item => {
                        var row = document.createElement('div');
                        row.className = 'item-row';
                        var icon = (currentTab === 'live') ? 'https://cdn-icons-png.flaticon.com/512/716/716429.png' : 'https://cdn-icons-png.flaticon.com/512/4221/4221359.png';
                        
                        row.innerHTML = '<img src="' + icon + '"><div class="item-details"><div class="item-name">' + item.name + '</div></div>';
                        row.onclick = function() { playVideo(item.direct_url, item.proxy_url, item.name, currentTab); };
                        itemsContainer.appendChild(row);
                    });
                }).catch(err => {
                    itemsContainer.innerHTML = '<div style="text-align:center; padding:20px; color:#ff3b30;">حدث خطأ أثناء تحميل البيانات من الخادم</div>';
                });
        }

        function playVideo(directUrl, proxyUrl, name, type) {
            document.getElementById('currentPlayingTitle').innerText = "يعرض الآن: " + name;
            if (hls) { hls.destroy(); hls = null; }

            var streamUrl = proxyUrl; // تشغيل البروكسي لإصلاح جدار الحماية

            if (type === 'live') {
                if (Hls.isSupported()) {
                    hls = new Hls({
                        enableWorker: true,
                        lowLatencyMode: true,
                        maxBufferLength: 30,
                        maxMaxBufferLength: 60,
                        xhrSetup: function(xhr, url) {
                            xhr.withCredentials = false;
                        }
                    });
                    hls.loadSource(streamUrl);
                    hls.attachMedia(videoElement);
                    hls.on(Hls.Events.MANIFEST_PARSED, function() { videoElement.play().catch(e => {}); });
                    
                    hls.on(Hls.Events.ERROR, function(event, data) {
                        if (data.fatal) {
                            if (streamUrl === proxyUrl) {
                                console.log("Fallback to direct URL...");
                                streamUrl = directUrl;
                                hls.loadSource(streamUrl);
                                hls.startLoad();
                            } else {
                                hls.recoverMediaError();
                            }
                        }
                    });
                } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
                    videoElement.src = streamUrl;
                    videoElement.play().catch(e => {
                        videoElement.src = directUrl;
                        videoElement.play().catch(err => {});
                    });
                }
            } else {
                videoElement.src = proxyUrl;
                videoElement.play().catch(err => {
                    videoElement.src = directUrl;
                    videoElement.play().catch(e => {});
                });
            }
        }

        showCategories();
    </script>
</body>
</html>
'''

# -------------------------------------------------------------
# 3. محاور التحكم الخلفية (Backend Routes)
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
    
    live_cats = safe_fetch(f"{base_api}&action=get_live_categories") or []
    vod_cats = safe_fetch(f"{base_api}&action=get_vod_categories") or []

    packaged_data = {
        "live_cats": live_cats,
        "vod_cats": vod_cats
    }
    return render_template_string(PLAYER_INTERFACE, data=packaged_data)

@app.route('/get_streams')
def get_streams():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')
    stream_type = request.args.get('type', 'live')
    category_id = request.args.get('category_id')

    if not host or not category_id:
        return jsonify([])

    base_api = f"{host}/player_api.php?username={username}&password={password}"
    action = "get_live_streams" if stream_type == "live" else "get_vod_streams"
    
    streams = safe_fetch(f"{base_api}&action={action}&category_id={category_id}")
    fallback_token = "HhQKUhFQEA8UVgNWWlALVAdVVFBTVwoNVFcDU1tSAgIDAVsEWl4AUw8SGUQRQEABVQg6DFRACQsDAwwAUklERBZTEGwLXBAPFAQBVlcGBUYYRxEMXQcRAwYeF0IKAUQLRwdTA1UKEBkUVU0SB0ZcBVg6AQBGC1BcFAhbRw8JShMKWD1XB1VTW1ISD0RSFh5GXRYVRwoMRlVaHhdQChEUUBFTQAlACgYFDhIZRAFbRwpAFxxHCkB3YxQeF1cbEQNfFl8NXUACEFgFRQ1EThZbF2sXABZEEFZYW1dHEFlHVhNJFA9SGmdRWlheUAUWXV0KR0dfRwFAHxtbXVtbFwoUbhVfBhFYGgUCBQMXGw=="

    parsed_results = []
    if isinstance(streams, list):
        for ch in streams:
            if ch.get("stream_id"):
                s_id = ch.get("stream_id")
                token = ch.get("token", fallback_token)
                
                if stream_type == 'live':
                    ext = ch.get("container_extension", "m3u8")
                    direct_url = f"{host}/live/{username}/{password}/{s_id}.{ext}?token={token}"
                    proxy_url = f"/proxy/live/{s_id}.{ext}?token={token}"
                else:
                    ext = ch.get("container_extension", "mp4")
                    direct_url = f"{host}/movie/{username}/{password}/{s_id}.{ext}"
                    proxy_url = f"/proxy/movie/{s_id}.{ext}"
                
                parsed_results.append({
                    "name": ch.get("name"),
                    "direct_url": direct_url,
                    "proxy_url": proxy_url
                })
    return jsonify(parsed_results)

# -------------------------------------------------------------
# 4. محرك البروكسي الشامل مع ميزة فك الضغط التلقائي للـ m3u8
# -------------------------------------------------------------
@app.route('/proxy/<path:stream_path>')
def proxy_stream(stream_path):
    host = flask_session.get('host')
    target_url = f"{host}/{stream_path}"
    if request.query_string: target_url += f"?{request.query_string.decode('utf-8')}"
    
    # إضافة Headers إضافية لمحاكاة متصفح منزلي
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": host + "/",
        "Origin": host
    }

    try:
        req = requests.get(target_url, headers=headers, stream=True, timeout=20)
        
        # 2. إذا كان ملف m3u8، نقوم بتعديله وتمريره
        if '.m3u8' in stream_path:
            content = req.text
            # استبدال روابط الـ ts لتمر عبر البروكسي
            fixed_content = re.sub(r'([^\s\n\r]+\.ts)', lambda m: f"/proxy/{stream_path.rsplit('/', 1)[0]}/{m.group(1)}", content)
            response = Response(fixed_content, content_type='application/x-mpegURL')
        else:
            # 3. تمرير ملفات الفيديو (ts) كما هي مع كافة رؤوس الاستجابة الأصلية
            response = Response(req.iter_content(chunk_size=1024*512), 
                                content_type=req.headers.get('Content-Type', 'video/mp2t'),
                                status=req.status_code)
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        return str(e), 500

# -------------------------------------------------------------
# 5. تحميل ملف الـ M3U
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
                                ext = item.get("container_extension", "m3u8" if block_type == "live" else "mp4")
                                yield f'#EXTINF:-1 group-title="{cat.get("category_name")}",{item.get("name")}\n'
                                yield f"{host}/{block_type}/{username}/{password}/{s_id}.{ext}\n"

    return Response(generate(), mimetype='text/plain', headers={"Content-Disposition": "attachment;filename=playlist.m3u"})

@app.route('/logout')
def logout():
    flask_session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

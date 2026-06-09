from flask import Flask, Response, render_template_string, request, redirect, url_for, session as flask_session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)
app.secret_key = "iptv_secret_secure_key_12345"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

http_session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=50, pool_maxsize=50)
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
# 1. واجهة صفحة تسجيل الدخول (Home)
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
        :root {
            --bg: linear-gradient(135deg, #09090e 0%, #150f24 100%);
            --card-bg: rgba(22, 17, 39, 0.7);
            --accent: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            --border: rgba(255, 255, 255, 0.06);
        }
        body { font-family: 'Tajawal', sans-serif; background: var(--bg); color: #fff; min-height: 100vh; margin: 0; display: flex; align-items: center; justify-content: center; padding: 20px; box-sizing: border-box; }
        .card { background: var(--card-bg); backdrop-filter: blur(20px); width: 100%; max-width: 440px; border-radius: 24px; padding: 40px; border: 1px solid var(--border); box-shadow: 0 20px 50px rgba(0,0,0,0.5); text-align: center; }
        h1 { margin: 0 0 10px 0; background: var(--accent); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 26px; }
        p.desc { color: #8a8594; font-size: 14px; margin-bottom: 30px; }
        .form-group { text-align: right; margin-bottom: 20px; }
        label { display: block; font-size: 13px; color: #b1a9bc; margin-bottom: 8px; }
        input { width: 100%; padding: 14px; background: rgba(10, 7, 20, 0.6); border: 1px solid var(--border); border-radius: 12px; color: #fff; font-size: 15px; box-sizing: border-box; transition: 0.3s; }
        input:focus { border-color: #00f2fe; outline: none; box-shadow: 0 0 12px rgba(0,242,254,0.2); }
        .btn-group { display: flex; gap: 10px; margin-top: 25px; }
        .btn { flex: 1; padding: 15px; border: none; border-radius: 12px; font-size: 15px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-primary { background: var(--accent); color: #09090e; box-shadow: 0 4px 15px rgba(0,242,254,0.2); }
        .btn-secondary { background: rgba(255,255,255,0.06); color: #fff; border: 1px solid var(--border); }
        .btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .loading { display: none; margin-top: 20px; color: #00f2fe; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>IPTV PORTAL PRO</h1>
        <p class="desc">ادخل بيانات سيرفر Xtream لتشغيل المحتوى فوراً أو تحميل الملف</p>
        <form id="loginForm" method="POST" action="/login">
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
        <div class="loading" id="loadStatus">جاري معالجة طلبك والاتصال بالسيرفر التدفقي...</div>
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
# 2. واجهة صفحة مشغل الفيديو المطور (Web Player)
# -------------------------------------------------------------
PLAYER_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>المشغل السينمائي المباشر</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
    
    <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
    <style>
        body { font-family: 'Tajawal', sans-serif; background: #0b0914; color: #fff; margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; }
        header { background: #141124; padding: 15px 25px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); }
        header h1 { margin: 0; font-size: 20px; color: #00f2fe; }
        .logout-btn { background: rgba(255, 59, 48, 0.2); color: #ff3b30; border: 1px solid rgba(255, 59, 48, 0.4); padding: 8px 16px; border-radius: 8px; cursor: pointer; text-decoration: none; font-size: 13px; }
        
        .main-layout { display: flex; flex: 1; overflow: hidden; }
        
        .video-section { flex: 2; background: #000; display: flex; flex-direction: column; justify-content: center; align-items: center; position: relative; border-left: 1px solid rgba(255,255,255,0.05); }
        .video-container { width: 100%; height: 100%; max-height: 85vh; display: flex; justify-content: center; align-items: center; }
        .video-js { width: 100% !important; height: 100% !important; }
        .video-title { position: absolute; top: 15px; left: 20px; background: rgba(0,0,0,0.7); padding: 8px 15px; border-radius: 6px; font-size: 14px; z-index: 10; color: #00f2fe; border: 1px solid rgba(255,255,255,0.05); }

        .content-sidebar { flex: 1; background: #110e1c; display: flex; flex-direction: column; overflow-y: auto; max-width: 400px; width: 100%; }
        .tabs { display: flex; background: #161226; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; font-weight: bold; font-size: 14px; color: #8a8594; transition: 0.2s; }
        .tab.active { color: #00f2fe; background: #110e1c; border-bottom: 2px solid #00f2fe; }
        
        .items-list { padding: 10px; overflow-y: auto; flex: 1; }
        .item-row { display: flex; align-items: center; padding: 12px 15px; border-bottom: 1px solid rgba(255,255,255,0.02); cursor: pointer; transition: 0.2s; }
        .item-row:hover { background: rgba(0, 242, 254, 0.08); }
        .item-row img { width: 40px; height: 40px; object-fit: contain; border-radius: 6px; background: rgba(0,0,0,0.3); margin-left: 12px; }
        .item-details { text-align: right; }
        .item-name { font-size: 14px; font-weight: 600; margin-bottom: 4px; color: #eaeaea; }
        .item-group { font-size: 11px; color: #6f6a7a; }

        @media (max-width: 768px) {
            .main-layout { flex-direction: column; }
            .content-sidebar { max-width: 100%; flex: 1; }
            .video-section { height: 40vh; flex: none; }
        }
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
                <video id="my-video" class="video-js vjs-default-skin vjs-big-play-centered" controls preload="auto">
                    <p class="vjs-no-js">المتصفح لا يدعم التشغيل المباشر.</p>
                </video>
            </div>
        </div>

        <div class="content-sidebar">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('live')">📺 قنوات مباشرة</div>
                <div class="tab" onclick="switchTab('vod')">🎬 أفلام سينما</div>
            </div>

            <div id="liveList" class="items-list">
                {% if data.live %}
                    {% for item in data.live %}
                        <div class="item-row" onclick="playVideo('{{ item.url }}', '{{ item.name }}', 'live')">
                            <img src="{{ item.icon if item.icon else 'https://cdn-icons-png.flaticon.com/512/716/716429.png' }}" onerror="this.src='https://cdn-icons-png.flaticon.com/512/716/716429.png'">
                            <div class="item-details">
                                <div class="item-name">{{ item.name }}</div>
                                <div class="item-group">{{ item.cat }}</div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div style="padding: 20px; color: #6f6a7a; text-align: center;">لا توجد قنوات متاحة أو السيرفر فارغ</div>
                {% endif %}
            </div>

            <div id="vodList" class="items-list" style="display: none;">
                {% if data.movies %}
                    {% for item in data.movies %}
                        <div class="item-row" onclick="playVideo('{{ item.url }}', '{{ item.name }}', 'vod')">
                            <img src="{{ item.icon if item.icon else 'https://cdn-icons-png.flaticon.com/512/4221/4221359.png' }}" onerror="this.src='https://cdn-icons-png.flaticon.com/512/4221/4221359.png'">
                            <div class="item-details">
                                <div class="item-name">{{ item.name }}</div>
                                <div class="item-group">{{ item.cat }}</div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div style="padding: 20px; color: #6f6a7a; text-align: center;">لا توجد أفلام في هذا السيرفر</div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
    <script>
        var player = videojs('my-video', {
            fluid: true,
            playbackRates: [0.5, 1, 1.5, 2]
        });

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

        function playVideo(url, name, type) {
            document.getElementById('currentPlayingTitle').innerText = "يعرض الآن: " + name;
            
            // تحديد الـ Type المناسب للمتصفح حتى يقرأ الـ Stream بشكل صحيح
            let streamType = 'video/mp4'; // الافتراضي للأفلام
            
            if (type === 'live') {
                // قنوات البث المباشر تحتاج لتعريفها كـ HLS/MPEGURL لتقبلها مشغلات الويب الحديثة
                streamType = 'application/x-mpegURL'; 
            } else if (url.includes('.m3u8')) {
                streamType = 'application/x-mpegURL';
            } else if (url.includes('.mkv')) {
                streamType = 'video/webm'; // معالجة بديلة لـ mkv داخل المتصفح
            }

            player.src({
                src: url,
                type: streamType
            });
            
            player.ready(function() {
                player.play().catch(function(error) {
                    console.log("فشل التشغيل التلقائي: ", error);
                });
            });

            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(LOGIN_INTERFACE)

@app.route('/login', methods=['POST'])
def login():
    host = request.form.get('host', '').strip().rstrip('/')
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    mode = request.form.get('mode', 'play')

    flask_session['host'] = host
    flask_session['username'] = username
    flask_session['password'] = password

    if mode == 'download':
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

    # 1. جلب القنوات المباشرة
    live_cats = safe_fetch(f"{base_api}&action=get_live_categories")
    if isinstance(live_cats, list):
        for cat in live_cats[:6]: 
            cat_id = cat.get("category_id")
            cat_name = cat.get("category_name")
            streams = safe_fetch(f"{base_api}&action=get_live_streams&category_id={cat_id}")
            if isinstance(streams, list):
                for ch in streams[:12]: 
                    stream_id = ch.get("stream_id")
                    if stream_id:
                        # تحسين هام: بعض السيرفرات تدعم بث m3u8 للمتصفحات بدلاً من ts الشاق
                        # سنقوم بتجربة الصيغة الأكثر استقراراً في المتصفح للـ Live
                        packaged_data["live"].append({
                            "name": ch.get("name", "Unknown Channel"),
                            "url": f"{host}/live/{username}/{password}/{stream_id}.ts",
                            "icon": ch.get("stream_icon"),
                            "cat": cat_name
                        })

    # 2. جلب الأفلام السينمائية
    vod_cats = safe_fetch(f"{base_api}&action=get_vod_categories")
    if isinstance(vod_cats, list):
        for cat in vod_cats[:6]: 
            cat_id = cat.get("category_id")
            cat_name = cat.get("category_name")
            streams = safe_fetch(f"{base_api}&action=get_vod_streams&category_id={cat_id}")
            if isinstance(streams, list):
                for movie in streams[:12]:
                    movie_id = movie.get("stream_id")
                    ext = movie.get("container_extension", "mp4")
                    if movie_id:
                        packaged_data["movies"].append({
                            "name": movie.get("name", "Unknown Movie"),
                            "url": f"{host}/movie/{username}/{password}/{movie_id}.{ext}",
                            "icon": movie.get("stream_icon"),
                            "cat": cat_name
                        })

    return render_template_string(PLAYER_INTERFACE, data=packaged_data)

@app.route('/download')
def download_m3u():
    host = flask_session.get('host')
    username = flask_session.get('username')
    password = flask_session.get('password')

    if not host or not username or not password:
        return redirect(url_for('home'))

    def generate():
        yield "#EXTM3U\n"
        base_api = f"{host}/player_api.php?username={username}&password={password}"
        
        for action, block_type in [("get_live_categories", "live"), ("get_vod_categories", "movie")]:
            cats = safe_fetch(f"{base_api}&action={action}")
            if isinstance(cats, list):
                for cat in cats:
                    cat_id = cat.get("category_id")
                    cat_name = cat.get("category_name")
                    stream_action = "get_live_streams" if block_type == "live" else "get_vod_streams"
                    streams = safe_fetch(f"{base_api}&action={stream_action}&category_id={cat_id}")
                    if isinstance(streams, list):
                        for item in streams:
                            s_id = item.get("stream_id")
                            if s_id:
                                ext = "ts" if block_type == "live" else item.get("container_extension", "mp4")
                                yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{item.get("stream_icon", "")}",{item.get("name")}\n'
                                yield f"{host}/{block_type}/{username}/{password}/{s_id}.{ext}\n"

    return Response(generate(), mimetype='text/plain', headers={"Content-Disposition": "attachment;filename=playlist.m3u"})

@app.route('/logout')
def logout():
    flask_session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

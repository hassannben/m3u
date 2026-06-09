from flask import Flask, Response, render_template_string, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# إعدادات الـ Headers لمحاكاة متصفح حقيقي وتجنب الحظر
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

# تحسين أداء الجلسة (Session) للتعامل مع آلاف الطلبات المتزامنة
session = requests.Session()
retry_strategy = Retry(
    total=3, 
    backoff_factor=0.2, 
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=50, pool_maxsize=50)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update(HEADERS)

def safe_fetch(url):
    """جلب البيانات بأمان مع تدوين الأخطاء وتجنب انهيار السيرفر"""
    try:
        response = session.get(url, timeout=12)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"⚠️ خطأ أثناء جلب الرابط [{url}]: {e}")
    return None

# واجهة مستخدم احترافية وعصرية (UI/UX)
HTML_INTERFACE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV M3U Toolkit Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f0c1b 0%, #201335 50%, #0b0914 100%);
            --panel-bg: rgba(25, 19, 44, 0.65);
            --accent: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
            --accent-hover: linear-gradient(90deg, #00e0ec 0%, #3b94eb 100%);
            --text-main: #ffffff;
            --text-muted: #a19da9;
            --border: rgba(255, 255, 255, 0.08);
        }
        
        body {
            font-family: 'Tajawal', 'Plus Jakarta Sans', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            box-sizing: border-box;
        }

        .card {
            background: var(--panel-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            width: 100%;
            max-width: 480px;
            border-radius: 24px;
            padding: 40px;
            border: 1px solid var(--border);
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }

        h1 {
            font-size: 26px;
            font-weight: 700;
            margin: 0 0 10px 0;
            background: var(--accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p.subtitle {
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 35px;
        }

        .form-group {
            text-align: right;
            margin-bottom: 22px;
            position: relative;
        }

        label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #c5c2cb;
            margin-bottom: 8px;
            padding-right: 4px;
        }

        input {
            width: 100%;
            padding: 14px 16px;
            background: rgba(10, 7, 18, 0.5);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-main);
            font-size: 15px;
            box-sizing: border-box;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        input:focus {
            outline: none;
            border-color: #00f2fe;
            background: rgba(10, 7, 18, 0.8);
            box-shadow: 0 0 0 4px rgba(0, 242, 254, 0.15);
        }

        input::placeholder {
            color: #555062;
        }

        .btn {
            width: 100%;
            padding: 16px;
            background: var(--accent);
            border: none;
            border-radius: 14px;
            color: #0f0c1b;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 15px;
            transition: all 0.2s ease;
            box-shadow: 0 8px 24px rgba(0, 242, 254, 0.25);
        }

        .btn:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
            box-shadow: 0 12px 28px rgba(0, 242, 254, 0.35);
        }

        /* أنيميشن التحميل الاحترافي */
        .loading-state {
            display: none;
            margin-top: 25px;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.05);
            border-top-color: #00f2fe;
            border-radius: 50%;
            margin: 0 auto 15px auto;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 13px;
            color: #00f2fe;
            font-weight: 600;
        }

        .footer-note {
            margin-top: 30px;
            font-size: 11px;
            color: #555062;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
            padding-top: 15px;
        }
    </style>
</head>
<body>

    <div class="card">
        <h1>IPTV TO M3U CONVERTER</h1>
        <p class="subtitle">قم بتحويل واختصار اشتراك Xtream الخاص بك إلى ملف سحري مباشر</p>
        
        <form id="iptvForm" action="/generate" method="POST" onsubmit="showLoading()">
            <div class="form-group">
                <label>رابط خادم السيرفر (Host URL)</label>
                <input type="url" name="host" placeholder="مثال: http://example.com:8080" required autocomplete="off">
            </div>
            <div class="form-group">
                <label>اسم المستخدم (Username)</label>
                <input type="text" name="username" placeholder="اليوزر نيم الخاص بحسابك" required autocomplete="off">
            </div>
            <div class="form-group">
                <label>كلمة المرور (Password)</label>
                <input type="password" name="password" placeholder="الرمز السري للحساب" required autocomplete="off">
            </div>
            <button type="submit" id="submitBtn" class="btn">توليد وبث قائمة التشغيل</button>
        </form>

        <div class="loading-state" id="loadingState">
            <div class="spinner"></div>
            <div class="loading-text">جاري الاتصال بالسيرفر واستخراج البيانات تدفقياً...</div>
        </div>

        <div class="footer-note">
            النظام يعتمد تقنية البث التدفقي (Streaming Response) لتحميل فوري وآمن دون تخزين بياناتك.
        </div>
    </div>

    <script>
        function showLoading() {
            document.getElementById('submitBtn').style.display = 'none';
            document.getElementById('loadingState').style.display = 'block';
            
            // إعادة الزر بعد 15 ثانية تلقائياً تحسباً لانتهاء التحميل أو حدوث خطأ
            setTimeout(() => {
                document.getElementById('submitBtn').style.display = 'block';
                document.getElementById('loadingState').style.display = 'none';
            }, 15000);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_INTERFACE)

@app.route('/generate', methods=['POST'])
def generate_m3u():
    # تنظيف المدخلات بدقة
    user_host = request.form.get('host', '').strip().rstrip('/')
    user_name = request.form.get('username', '').strip()
    user_pass = request.form.get('password', '').strip()

    if not user_host or not user_name or not user_pass:
        return "بيانات غير صالحة، يرجى ملء الحقول المطلوبة.", 400

    def generate():
        yield "#EXTM3U\n"
        
        base_api = f"{user_host}/player_api.php?username={user_name}&password={user_pass}"

        # --- 1. معالجة البث المباشر (LIVE) ---
        live_cats = safe_fetch(f"{base_api}&action=get_live_categories")
        if isinstance(live_cats, list):
            for cat in live_cats:
                cat_id = cat.get("category_id")
                cat_name = cat.get("category_name", "عام")
                if not cat_id: continue
                
                streams = safe_fetch(f"{base_api}&action=get_live_streams&category_id={cat_id}")
                if isinstance(streams, list):
                    for ch in streams:
                        try:
                            name = ch.get("name", "قناة غير معروفة")
                            stream_id = ch.get("stream_id")
                            icon = ch.get("stream_icon", "")
                            if stream_id:
                                yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{icon}",{name}\n'
                                yield f"{user_host}/live/{user_name}/{user_pass}/{stream_id}.ts\n"
                        except Exception:
                            continue

        # --- 2. معالجة الأفلام (VOD) ---
        vod_cats = safe_fetch(f"{base_api}&action=get_vod_categories")
        if isinstance(vod_cats, list):
            for cat in vod_cats:
                cat_id = cat.get("category_id")
                cat_name = cat.get("category_name", "أفلام")
                if not cat_id: continue
                
                streams = safe_fetch(f"{base_api}&action=get_vod_streams&category_id={cat_id}")
                if isinstance(streams, list):
                    for movie in streams:
                        try:
                            name = movie.get("name", "فيلم غير معروف")
                            icon = movie.get("stream_icon", "")
                            if "stream_url" in movie and movie["stream_url"]:
                                movie_url = movie["stream_url"]
                            else:
                                movie_id = movie.get("stream_id")
                                container = movie.get("container_extension", "mp4")
                                movie_url = f"{user_host}/movie/{user_name}/{user_pass}/{movie_id}.{container}" if movie_id else ""
                            
                            if movie_url:
                                yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{icon}",{name}\n'
                                yield f"{movie_url}\n"
                        except Exception:
                            continue

        # --- 3. معالجة المسلسلات (SERIES) ---
        series_cats = safe_fetch(f"{base_api}&action=get_series_categories")
        if isinstance(series_cats, list):
            for cat in series_cats:
                cat_id = cat.get("category_id")
                cat_name = cat.get("category_name", "مسلسلات")
                if not cat_id: continue
                
                series_list = safe_fetch(f"{base_api}&action=get_series&category_id={cat_id}")
                if isinstance(series_list, list):
                    for s in series_list:
                        try:
                            name = s.get("name", "مسلسل غير معروف")
                            icon = s.get("stream_icon", "")
                            series_id = s.get("series_id")
                            if series_id:
                                yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{icon}",{name}\n'
                                yield f"{user_host}/series/{user_name}/{user_pass}/{series_id}.mp4\n"
                        except Exception:
                            continue

    # بث الملف تدفقياً بصيغة text/plain مع إجبار المتصفح على تحميله كملف .m3u
    return Response(
        generate(), 
        mimetype='text/plain', 
        headers={"Content-Disposition": "attachment;filename=playlist.m3u"}
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

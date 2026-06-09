from flask import Flask, Response, render_template_string, request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

# إعداد الجلسة لسرعة الاستجابة وإعادة المحاولة عند الفشل
session = requests.Session()
retry = Retry(total=2, read=2, connect=2, backoff_factor=0.1, status_forcelist=(500, 502, 504))
adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
session.mount('http://', adapter)
session.mount('https://', adapter)
session.headers.update(headers)

def fetch_data(url):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return None

# واجهة الموقع (صفحة تسجيل البيانات)
@app.route('/')
def home():
    html = '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مولد ملفات IPTV M3U</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a2e; color: #fff; text-align: center; margin: 0; padding: 20px; }
            .container { max-width: 500px; margin: 60px auto; background: #161623; padding: 40px; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05); }
            h1 { color: #00fff0; margin-bottom: 30px; font-size: 28px; }
            .form-group { text-align: right; margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #bbb; font-size: 14px; }
            input { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #0f0f1a; color: #fff; box-sizing: border-box; font-size: 16px; transition: 0.3s; }
            input:focus { border-color: #00fff0; outline: none; box-shadow: 0 0 10px rgba(0,255,240,0.2); }
            .btn { width: 100%; padding: 14px; background: linear-gradient(45deg, #00fff0, #0081ff); border: none; border-radius: 8px; color: white; font-size: 18px; font-weight: bold; cursor: pointer; margin-top: 10px; transition: 0.3s; }
            .btn:hover { opacity: 0.9; transform: translateY(-2px); }
            .note { margin-top: 25px; font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 مستخرج ملفات M3U الشامل</h1>
            <form action="/generate" method="POST">
                <div class="form-group">
                    <label>رابط السيرفر (Host):</label>
                    <input type="url" name="host" placeholder="مثال: http://alp1.vip/" required>
                </div>
                <div class="form-group">
                    <label>اسم المستخدم (Username):</label>
                    <input type="text" name="username" placeholder="أدخل اليوزر نيم" required>
                </div>
                <div class="form-group">
                    <label>كلمة المرور (Password):</label>
                    <input type="password" name="password" placeholder="أدخل الباسورد" required>
                </div>
                <button type="submit" class="btn">توليد وتحميل الملف فوراً</button>
            </form>
            <div class="note">ملاحظة: قد يستغرق بدء التحميل بضع ثوانٍ بناءً على حجم السيرفر الخاص بك.</div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

# الرابط المسؤول عن استقبال البيانات وتوليد الملف وبثه للمستخدم
@app.route('/generate', methods=['POST'])
def generate_m3u():
    # استقبال البيانات المدخلة من الفورم تنظيف الفراغات الزائدة
    user_host = request.form.get('host').strip().rstrip('/')
    user_name = request.form.get('username').strip()
    user_pass = request.form.get('password').strip()

    def generate():
        yield "#EXTM3U\n"
        
        # 1. جلب القنوات المباشرة
        live_cats = fetch_data(f"{user_host}/player_api.php?username={user_name}&password={user_pass}&action=get_live_categories")
        if live_cats and isinstance(live_cats, list):
            for cat in live_cats:
                cat_id = cat.get("category_id")
                cat_name = cat.get("category_name")
                streams = fetch_data(f"{user_host}/player_api.php?username={user_name}&password={user_pass}&action=get_live_streams&category_id={cat_id}")
                if streams and isinstance(streams, list):
                    for ch in streams:
                        name = ch.get("name", "Unknown")
                        stream_id = ch.get("stream_id")
                        icon = ch.get("stream_icon", "")
                        if stream_id:
                            yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{icon}",{name}\n'
                            yield f"{user_host}/live/{user_name}/{user_pass}/{stream_id}.ts\n"

        # 2. جلب الأفلام 
        vod_cats = fetch_data(f"{user_host}/player_api.php?username={user_name}&password={user_pass}&action=get_vod_categories")
        if vod_cats and isinstance(vod_cats, list):
            for cat in vod_cats:
                cat_id = cat.get("category_id")
                cat_name = cat.get("category_name")
                streams = fetch_data(f"{user_host}/player_api.php?username={user_name}&password={user_pass}&action=get_vod_streams&category_id={cat_id}")
                if streams and isinstance(streams, list):
                    for movie in streams:
                        name = movie.get("name", "Unknown")
                        icon = movie.get("stream_icon", "")
                        if "stream_url" in movie and movie["stream_url"]:
                            movie_url = movie["stream_url"]
                        else:
                            movie_id = movie.get("stream_id", "")
                            movie_url = f"{user_host}/movie/{user_name}/{user_pass}/{movie_id}.mp4" if movie_id else ""
                        if movie_url:
                            yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{icon}",{name}\n'
                            yield f"{movie_url}\n"

        # 3. جلب المسلسلات
        series_cats = fetch_data(f"{user_host}/player_api.php?username={user_name}&password={user_pass}&action=get_series_categories")
        if series_cats and isinstance(series_cats, list):
            for cat in series_cats:
                cat_id = cat.get("category_id")
                cat_name = cat.get("category_name")
                series_list = fetch_data(f"{user_host}/player_api.php?username={user_name}&password={user_pass}&action=get_series&category_id={cat_id}")
                if series_list and isinstance(series_list, list):
                    for s in series_list:
                        name = s.get("name", "Unknown")
                        icon = s.get("stream_icon", "")
                        series_id = s.get("series_id", "")
                        if series_id:
                            yield f'#EXTINF:-1 group-title="{cat_name}" tvg-logo="{icon}",{name}\n'
                            yield f"{user_host}/series/{user_name}/{user_pass}/{series_id}.mp4\n"

    # إرجاع الملف مباشرة للمتصفح ليبدأ بالتحميل بصيغة m3u
    return Response(
        generate(), 
        mimetype='text/plain', 
        headers={"Content-Disposition": "attachment;filename=playlist.m3u"}
    )

if __name__ == '__main__':
    # تشغيل السيرفر محلياً
    app.run(debug=True, host='0.0.0.0', port=5000)
<div dir="rtl">

# مشارکت در پروژه 🤝

از مشارکت شما استقبال می‌شود!

## راه‌های مشارکت
- گزارش باگ و پیشنهاد قابلیت در [Issues](https://github.com/100ri-ir/NumLockLight/issues)
- ارسال Pull Request برای بهبود کد یا ترجمه
- معرفی برنامه به دیگران ⭐

## راهنمای فنی

### اجرای سورس (ویندوز)
```bat
py -3 -m pip install -r requirements.txt
py -3 -m src\numlocklight
```

### اجرای نسخه توسعه (لینوکس/تست UI)
```bash
pip install pystray pillow arabic-reshaper python-bidi
python3 -m src.numlocklight --dev
```
> نکته: در ویندوز متن فارسی توسط خود Tk شکل‌دهی می‌شود؛ در لینوکس فقط برای
> تست/اسکرین‌شات از `arabic-reshaper` و `python-bidi` استفاده می‌شود.

### قواعد کد
- کد را با `python -m py_compile src/numlocklight/*.py` بررسی کنید.
- رابط کاربری باید RTL و فارسی بماند (`fa()` برای همه متن‌ها).
- قبل از ارسال، یک بار `build\Build_Portable.bat ci` را اجرا کنید تا از
  سالم بودن بیلد مطمئن شوید.

### ساختار پوشه‌ها
تغییرات را در پکیج `src/numlocklight` اعمال کنید؛ منابع (فونت/صدا/آیکون)
فقط از منابع آزاد و با مجوز قابل توزیع اضافه شوند و در `assets/CREDITS`
ذکر شوند.

</div>

# 📚 ForNote — یادداشت‌ساز هوشمند از کتاب

آپلود کتاب‌های سنگین پزشکی (PDF) → یادداشت فصل‌به‌فصل + پرسش‌وپاسخ از متن کتاب.

## اجرا

```bash
pip install -r requirements.txt
python main.py
```

سپس مرورگر: **http://127.0.0.1:8000**

## دو حالت

| حالت | نیاز | توضیح |
|---|---|---|
| ✨ **Gemini (رایگان)** | کلید API رایگان | یادداشت‌های هوشمند، خلاصه، اصطلاحات، نکات امتحانی |
| 🔌 **آفلاین** | هیچ | خلاصه‌سازی استخراجی + اصطلاحات پرتکرار + جست‌وجوی TF-IDF — بدون هیچ مدلی |

### کلید رایگان Gemini (بدون کارت بانکی)
1. برو به https://aistudio.google.com/apikey
2. «Create API key» بزن و کلید را کپی کن
3. قبل از اجرا:
   - Windows (PowerShell):  `$env:GEMINI_API_KEY="کلید شما"`
   - یا در فایل `ai.py` خط `GEMINI_KEY` را مستقیم بگذار

## API

- `POST /upload` — فایل PDF → شناسه کتاب + فهرست فصل‌ها
- `POST /notes` — book_id + chapter → یادداشت مارک‌داون
- `POST /ask` — book_id + question → پاسخ + منابع

## ساختار

```
fornote/
├── main.py          # FastAPI (upload / notes / ask)
├── book_engine.py   # استخراج PDF، تکه‌بندی فصلی، خلاصه آفلاین، جست‌وجو
├── ai.py            # Gemini free API + حالت آفلاین خودکار
├── static/index.html# رابط کاربری فارسی
└── requirements.txt
```

MIT License

# SecureChat

منصة ويب لغرف اجتماعات خاصة. الأعضاء المعتمدون يدخلون اجتماعاً صوتياً ومرئياً عبر LiveKit بعد موافقة المالك.

## هيكل المشروع

```text
.
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── styles/
│   ├── vite.config.js
│   └── .env.example
├── start.sh
├── start-production.sh
├── Dockerfile
├── render.yaml
└── README.md
```

## ما يعمل حالياً

- جلسة مؤقتة آمنة عبر كوكي HttpOnly مع حماية CSRF
- إنشاء غرفة وحفظها في SQLite
- إنشاء دعوات برموز عشوائية قوية، مع حد استخدام وصلاحية وإبطال
- صفحة `/join/:code` مرتبطة بالخادم
- طلبات انضمام بحالة `pending` حتى قرار المالك
- قبول ورفض الطلبات من المالك فقط
- دخول واجهة الغرفة للأعضاء المعتمدين فقط
- تحديثات فورية عبر WebSocket للمالك والأعضاء المعتمدين
- إصدار رمز LiveKit من الخادم بعد التحقق من العضوية، عند توفر بيانات الاعتماد
- اتصال صوت وصورة حقيقي عبر WebRTC بين الأعضاء المعتمدين بدون خادم LiveKit
- اتصال LiveKit اختياري عندما تكون بيانات الاعتماد موجودة على الخادم
- واجهة عربية RTL متجاوبة
- ترويسات أمنية، حد معدل لإنشاء الغرف، وإبطال الجلسة عند الخروج
- إغلاق WebSocket للأعضاء غير المالكين بعد إغلاق الغرفة

- إنشاء حساب بالبريد وكلمة المرور، مع رمز تحقق لمدة 60 ثانية يُرسل عبر SMTP عند ضبطه

## ما لا يعمل بعد

- مشاركة الشاشة والتسجيل
- تسجيل الدخول بعد إنشاء الحساب (الجزء التالي)
- مشاركة شاشة متعددة المشاركين عبر خادم SFU خارجي عندما يتجاوز الند للند حدود الشبكة

## المتطلبات

- Python 3.11 أو أحدث
- Node.js 18 أو أحدث
- npm

## إعداد البيئة

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

في التطوير، `CORS_ORIGINS` محدودة بعنوان واجهة Vite. لا تستخدم `*` في الإنتاج.

الصوت والصورة يعملان افتراضياً عبر WebRTC بين الأعضاء المعتمدين، مع إشارة عبر WebSocket الحالي. لا تُوضع أسرار في الواجهة.

LiveKit اختياري لشبكات NAT المعقدة أو الغرف الكبيرة. إن توفرت بيانات اعتماد، انسخها إلى `backend/.env` فقط:

```bash
LIVEKIT_URL=wss://your-livekit-host
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
LIVEKIT_PUBLIC_URL=
WEBRTC_FALLBACK=true
```

بدون هذه القيم يبقى مسار `/livekit-token` يعيد 503، وتتصل الواجهة عبر الند للند. المتصفح يطلب الكاميرا/الميكروفون عبر `getUserMedia`، ولذلك يلزم HTTPS خارج localhost. STUN العام مستخدم في مسار WebRTC؛ شبكات NAT المتماثلة قد تحتاج TURN أو LiveKit.

إرسال رمز تأكيد الحساب يحتاج SMTP على الخادم فقط. انسخ القيم إلى `backend/.env` أو متغيرات بيئة النشر، ولا تضعها في الواجهة أو Git:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_ENCRYPTION=starttls
SMTP_USERNAME=your-gmail-address
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-gmail-address
SMTP_FROM_NAME=SecureChat
```

Gmail يتطلب كلمة مرور تطبيق وليس كلمة مرور الحساب. المنفذ `465` يستخدم `SMTP_ENCRYPTION=ssl`. بدون هذه القيم يُنشأ الحساب ويُحفظ الرمز، لكن الرسالة توضح أن الإرسال غير مضبوط ولا يُدّعى وصول البريد.

إعداد LiveKit الخارجي (لا تُخزَّن المفاتيح في الواجهة أو المستودع):

1. أنشئ مشروعاً في LiveKit Cloud أو شغّل خادماً ذاتياً يمكن للمتصفح الوصول إليه عبر `wss`.
2. انسخ `LIVEKIT_URL` و`LIVEKIT_API_KEY` و`LIVEKIT_API_SECRET` إلى `backend/.env` فقط.
3. إذا كان الخادم داخلياً (`ws://127.0.0.1`) ضع `LIVEKIT_PUBLIC_URL` بعنوان عام `wss` يصل إليه المتصفح.
4. أعد تشغيل الخادم. نقطة `/api/health` تعرض `livekit_configured` و`media_provider`.

## تثبيت الخادم وتشغيله

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

الخادم يعمل على `http://localhost:8000`.

نقطة الصحة: `GET http://localhost:8000/api/health`

توثيق التطوير: `http://localhost:8000/api/docs`

## تثبيت الواجهة وتشغيلها

```bash
cd frontend
npm install
npm run dev
```

الواجهة تعمل على `http://localhost:5173`.

طلبات `/api` تُمرَّر إلى الخادم عبر reverse proxy في `vite.config.js`.

## تشغيل الاثنين معاً

```bash
chmod +x start.sh
./start.sh
```

المنفذ المعروض للمعاينة هو منفذ الواجهة `5173`.

## النشر التجريبي على Render

الخدمة الواحدة تقدّم الواجهة وواجهة البرمجة من المنفذ نفسه. طلبات `/api` وWebSocket تبقى على نفس الأصل، لذلك لا حاجة لـ CORS مفتوح ولا لـ `COOKIE_SAMESITE=none`.

### ما يجب إعداده خارج هذا المستودع

هذه الخطوات ينفّذها صاحب الحساب، وليست جزءاً من تشغيل البيئة الحالية:

1. ارفع المستودع إلى GitHub أو GitLab.
2. أنشئ حساباً مجانياً على [Render](https://render.com) واربط المستودع.
3. انشر خدمة Web من `render.yaml` أو أنشئ خدمة Docker يدوياً من `Dockerfile`.
4. بعد ظهور عنوان `https://<service>.onrender.com` انسخه إلى `PUBLIC_ORIGIN` إن رغبت، أو اترك `CORS_ORIGINS` فارغاً لأن الواجهة والخادم على الأصل نفسه.
5. اختياري: أنشئ مشروعاً مجانياً في [LiveKit Cloud](https://cloud.livekit.io)، ثم أضف في لوحة Render فقط:
   - `LIVEKIT_URL` مثل `wss://<project>.livekit.cloud`
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
6. أعد نشر الخدمة بعد حفظ المتغيرات. لا تضع المفاتيح في الواجهة أو في Git.

بدون مفاتيح LiveKit يبقى الصوت والصورة عبر WebRTC بين الأعضاء المعتمدين. المتصفح يطلب الكاميرا والميكروفون، وRender يوفّر HTTPS وهذا مطلوب خارج localhost.

### متغيرات الإنتاج

| المتغير | مطلوب | ملاحظات |
| --- | --- | --- |
| `APP_ENV` | نعم | `production` |
| `COOKIE_SECURE` | نعم على HTTPS | `true` |
| `COOKIE_SAMESITE` | لا | `lax` عند نفس الأصل |
| `WEBRTC_FALLBACK` | لا | الافتراضي `true` |
| `DATABASE_URL` | لا | `sqlite:///./securechat.db` أو مسار على قرص |
| `FRONTEND_DIST_DIR` | في Docker | `/app/frontend/dist` |
| `CORS_ORIGINS` | لا | اتركه فارغاً لنفس الأصل؛ ممنوع `*` |
| `PUBLIC_ORIGIN` | لا | عنوان HTTPS العام إن وُجدت واجهة منفصلة |
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | لا | من LiveKit Cloud فقط، عبر لوحة Render |
| `SMTP_HOST` | نعم لإرسال التحقق | مثل `smtp.gmail.com` |
| `SMTP_PORT` | لا | `587` لـ STARTTLS أو `465` لـ SSL |
| `SMTP_ENCRYPTION` | لا | `starttls` أو `ssl` أو `none` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | غالباً | حساب SMTP أو كلمة مرور تطبيق Gmail |
| `SMTP_FROM_EMAIL` أو `SMTP_FROM` | نعم لإرسال التحقق | عنوان المرسل |
| `SMTP_FROM_NAME` | لا | الاسم الظاهر للمستلم |

الخطة المجانية على Render بلا قرص دائم: ملف SQLite يُفقد عند إعادة التشغيل أو إعادة النشر. لبقاء الغرف والدعوات أضف Disk على مسار مثل `/data` واضبط `DATABASE_URL=sqlite:////data/securechat.db`. هذا يتطلب خطة مدفوعة على Render.

### تشغيل أصلي بدون Docker

```bash
cd frontend
npm install
npm run build
cd ../backend
python3 -m pip install -r requirements.txt
cd ..
APP_ENV=production ./start-production.sh
```

`start-production.sh` يقدّم الواجهة المبنية من `frontend/dist` مع واجهة البرمجة على المنفذ `PORT`.

### التحقق بعد النشر

- `GET https://<service>.onrender.com/api/health` يعيد `status=ok` و`media_provider`.
- افتح الموقع من جهازين حقيقيين على HTTPS قبل اعتبار الصوت/الصورة ناجحاً. هذه البيئة لا تختبر الكاميرا أو الميكروفون.

## الاختبارات

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest
```

الاختبارات تستخدم قاعدة SQLite منفصلة في الذاكرة، وتغطي إنشاء الغرف والدعوات وطلبات الانضمام والصلاحيات ورفض رموز LiveKit لغير الأعضاء.

## مسارات API الأساسية

- `GET /api/health`
- `POST /api/session` و `GET /api/session`
- `POST /api/rooms` و `GET /api/rooms` و `GET /api/rooms/{id}`
- `POST /api/rooms/{id}/close`
- `POST /api/rooms/{id}/invitations`
- `POST /api/invitations/{id}/revoke`
- `GET /api/invites/{code}`
- `POST /api/join-requests`
- `GET /api/join-requests/{id}`
- `POST /api/join-requests/{id}/decision`
- `GET /api/rooms/{id}/meeting`
- `POST /api/rooms/{id}/livekit-token` للأعضاء المعتمدين فقط
- `WS /api/ws/rooms/{id}` قناة الغرفة للأعضاء المعتمدين
- `WS /api/ws/join-requests/{id}` قناة حالة الطلب لمقدمه
- `GET /api/accounts/captcha`
- `POST /api/accounts/register`
- `POST /api/accounts/verify-email`
- `POST /api/accounts/resend-verification`

## ملاحظات أمنية

- لا تضع مفاتيح حقيقية في المستودع. مفاتيح LiveKit تبقى في بيئة الخادم فقط.
- رموز الدعوة تُحفظ كبصمة SHA-256 فقط.
- الجلسة عبر كوكي HttpOnly، وطلبات التعديل تتطلب ترويسة `X-CSRF-Token`.
- رمز LiveKit لا يُصدر إلا بعد `require_room_access`.
- في الإنتاج تُعطَّل وثائق OpenAPI ويُرفض CORS المفتوح.

# هيكل مشروع SecureChat — توثيق مرجعي

هذا الملف يصف المشروع كما هو موجود فعلياً في المجلد الرئيسي. الأسماء والمسارات مأخوذة من الملفات على القرص. لم تُختلق مجلدات أو صفحات غير موجودة. ما لم يُتحقق منه في التشغيل الحي مُعلَّم بعبارة «غير متحقق منه».

---

## 1. شجرة المشروع مع الشرح في نفس السطر

المجلد الجذر على القرص هو مسار العمل الحالي للمشروع (SecureChat). الحجم التقريبي للمجال كله نحو 96M، معظمها في `frontend/node_modules`.

```text
.
│
├── PROJECT_STRUCTURE_AR.md              # هذا الملف: توثيق الهيكل والتقنيات والواجهات بالعربية.
├── README.md                            # دليل التشغيل والنشر والمتغيرات العامة بدون أسرار.
├── Dockerfile                           # بناء متعدد المراحل: Vite ثم صورة Python تقدّم الواجهة والخادم معاً.
├── render.yaml                          # تعريف خدمة Render المجانية ومسار الصحة ومتغيرات الإنتاج غير السرية.
├── start.sh                             # تشغيل التطوير: uvicorn على :8000 وVite على :5173.
├── start-production.sh                  # تشغيل الإنتاج: uvicorn يقدّم API وملفات frontend/dist.
├── .gitignore                           # تجاهل .env وnode_modules وdist وقواعد *.db والكاش.
├── .dockerignore                        # استبعاد Git و.env وnode_modules وملفات القاعدة من صورة Docker.
├── .git/                                # مستودع Git — مولَّد، لا يُفضَّل نسخه يدوياً.
├── .monkeycode-tmp-files/               # أرشيف مؤقت لأدوات المنصة، ليس جزءاً من منطق التطبيق.
│   ├── .gitignore                       # تجاهل محتويات المجلد المؤقت.
│   └── bbe0b622-workspace_2-1.zip       # أرشيف مؤقت — مولَّد.
├── securechat.db                        # نسخة SQLite قديمة في الجذر بمخطط غرف بلا أعمدة الحساب.
├── securechat.db-shm                    # ملف ذاكرة مشتركة لـ SQLite في الجذر — مولَّد.
├── securechat.db-wal                    # سجل WAL لنسخة الجذر — مولَّد.
│
├── scripts/                             # سكربتات بناء مساعدة للنشر بدون Docker.
│   └── render-build.sh                  # تثبيت وبناء الواجهة ثم تثبيت حزم بايثون.
│
├── frontend/                            # الواجهة الأمامية: React + Vite، صفحات المستخدم كلها هنا.
│   ├── .env                             # إعداد محلي للواجهة — لا يُعرض محتواه ولا يُلتزم به في Git.
│   ├── .env.example                     # قالب VITE_APP_NAME وVITE_API_BASE_URL=/api.
│   ├── index.html                       # نقطة HTML: اللغة عربية RTL، خط Google، وعنصر #root.
│   ├── package.json                     # اسم الحزمة وأوامر dev/build/preview/test واعتماديات الواجهة.
│   ├── package-lock.json                # قفل إصدارات npm — موجود رغم إدراجه في .gitignore.
│   ├── vite.config.js                   # منفذ 5173 وallowedHosts وبروكسي /api وWebSocket إلى :8000.
│   ├── dist/                            # مخرجات vite build — مولَّد نحو 800K — لا تُطبع محتوياته.
│   ├── node_modules/                    # حزم npm — مولَّد نحو 90M — لا تُطبع آلاف الملفات.
│   └── src/                             # المصدر البرمجي للواجهة.
│       ├── main.jsx                     # تركيب React وBrowserRouter واستيراد CSS العام.
│       ├── App.jsx                      # تعريف كل مسارات الصفحات داخل AppLayout.
│       ├── meetingLayout.js             # حساب صنف شبكة الفيديو حسب عدد المشاركين.
│       ├── meetingLayout.test.js        # اختبارات node:test لتخطيط شبكة الاجتماع فقط.
│       ├── api/                         # طبقة الاتصال بالخادم عبر fetch.
│       │   └── client.js                # كل استدعاءات REST وإرسال كوكي CSRF sc_csrf.
│       ├── components/                  # مكوّنات مشتركة بلا مجلدات فرعية auth/rooms/meeting.
│       │   ├── AppLayout.jsx            # الهيكل العام: ترويسة، روابط تنقل، تذييل، Outlet للصفحات.
│       │   ├── ActionButton.jsx         # زر بإصدارات primary وsecondary وghost.
│       │   ├── TextField.jsx            # حقل إدخال أو textarea للنماذج.
│       │   ├── PageHeader.jsx           # عنوان الصفحة مع kicker ووصف.
│       │   ├── StatusBanner.jsx         # شريط رسالة نجاح أو تحذير أو خطأ.
│       │   ├── ConnectionStatus.jsx     # شريحة حالة اتصال WebSocket.
│       │   └── ParticipantTile.jsx      # بلاطة فيديو/صوت لمشارك في الاجتماع.
│       ├── hooks/                       # خطافات React للزمن الحقيقي والوسائط.
│       │   ├── useRealtime.js           # WebSocket مع ping وإعادة اتصال وإرسال إشارات.
│       │   ├── useWebRtc.js             # اتصال الند للند: getUserMedia وRTCPeerConnection.
│       │   └── useLiveKit.js            # عميل LiveKit عندما media_provider=livekit.
│       ├── pages/                       # صفحات المسارات الظاهرة في المتصفح — مسطحة بلا مجلدات فرعية.
│       │   ├── HomePage.jsx             # الواجهة الرئيسية / : حالة الخادم وغرف الجلسة وروابط الإنشاء والانضمام.
│       │   ├── RegisterPage.jsx         # واجهة إنشاء حساب /register : بيانات وCAPTCHA بدون فتح جلسة قبل التأكيد.
│       │   ├── VerifyEmailPage.jsx      # واجهة تأكيد البريد /verify-email : رمز 6 أرقام وإعادة إرسال.
│       │   ├── LoginPage.jsx            # واجهة تسجيل الدخول /login : صفحة نائبة «قريباً» بلا نموذج عامل.
│       │   ├── CreateRoomPage.jsx       # واجهة إنشاء غرفة /create : اسم ووصف وحد مشاركين ودعوة أولية.
│       │   ├── JoinRoomPage.jsx         # واجهة الانضمام /join و/join/:code : معاينة الدعوة وطلب الانضمام.
│       │   ├── WaitingApprovalPage.jsx  # واجهة انتظار الموافقة /waiting/:requestId : حالة الطلب عبر WebSocket.
│       │   ├── RoomManagePage.jsx       # واجهة إدارة الغرفة /rooms/:roomId : دعوات وطلبات وأعضاء وإغلاق.
│       │   ├── MeetingPage.jsx          # واجهة الاجتماع /rooms/:roomId/meeting : صوت وصورة وشريط التحكم.
│       │   └── NotFoundPage.jsx         # واجهة 404 لأي مسار غير معرَّف.
│       └── styles/                      # تنسيق الواجهة بالكامل بملف واحد.
│           └── index.css                # ألوان RTL وتجاوب الهاتف وشبكة الفيديو ومكوّنات النماذج.
│
└── backend/                             # الخادم الخلفي: FastAPI وSQLAlchemy وWebSocket وSMTP.
    ├── .env                             # إعداد الخادم المحلي — لا يُطبع ولا يُرفع إلى Git.
    ├── .env.example                     # قالب متغيرات الجلسة وCORS وLiveKit وSMTP وحدود المعدل.
    ├── pytest.ini                       # إعداد pytest: مسار tests وpythonpath.
    ├── requirements.txt                 # حزم بايثون بإصدارات مثبتة.
    ├── securechat.db                    # قاعدة SQLite التشغيلية عند تشغيل الخادم من مجلد backend.
    ├── securechat.db-shm                # ذاكرة مشتركة لقاعدة backend — مولَّد.
    ├── securechat.db-wal                # سجل WAL لقاعدة backend — مولَّد.
    ├── .pytest_cache/                   # كاش pytest — مولَّد نحو 36K.
    ├── app/                             # حزمة التطبيق الأساسية.
    │   ├── __init__.py                  # إصدار الحزمة النصي 0.1.0.
    │   ├── main.py                      # مصنع FastAPI: CORS وترويسات أمنية ومسارات وربط SPA.
    │   ├── config.py                    # قراءة الإعداد من البيئة وخصائص SMTP وLiveKit والكوكيز.
    │   ├── database.py                  # محرك SQLAlchemy وinit_db وترحيل أعمدة الحساب على SQLite.
    │   ├── deps.py                      # اعتمادات FastAPI: المستخدم الحالي أو الاختياري من الجلسة.
    │   ├── errors.py                    # دوال HTTPException برسائل عربية موحّدة.
    │   ├── rate_limit.py                # حد معدل في ذاكرة العملية حسب المفتاح والنافذة الزمنية.
    │   ├── security.py                  # توليد الرموز وهاش SHA-256 وكوكيز الجلسة وCSRF.
    │   ├── static_spa.py                # تقديم frontend/dist لأي مسار ليس تحت /api.
    │   ├── models/                      # نماذج SQLAlchemy للجداول.
    │   │   ├── __init__.py              # تصدير User وSession وCaptcha وEmailVerification وجداول الغرف.
    │   │   ├── identity.py              # جداول users وsessions وcaptcha_challenges وemail_verifications.
    │   │   └── rooms.py                 # جداول rooms وroom_members وinvitations وjoin_requests.
    │   ├── routers/                     # مسارات HTTP REST.
    │   │   ├── __init__.py              # تجميع routers بما فيها ws_router.
    │   │   ├── health.py                # GET /api/health لفحص قاعدة البيانات ومسار الوسائط.
    │   │   ├── session.py               # GET/POST/DELETE /api/session لجلسة الضيف والخروج.
    │   │   ├── accounts.py              # مسارات CAPTCHA والتسجيل وتأكيد البريد وإعادة الإرسال.
    │   │   └── rooms.py                 # مسارات الغرف والدعوات وطلبات الانضمام والاجتماع ورمز LiveKit.
    │   ├── schemas/                     # عقود Pydantic للطلبات والاستجابات.
    │   │   ├── __init__.py              # تصدير نماذج الصحة والجلسة وملخص الغرفة.
    │   │   ├── health.py                # شكل استجابة الصحة.
    │   │   ├── identity.py              # طلب/استجابة جلسة الضيف باسم العرض.
    │   │   ├── accounts.py              # طلبات التسجيل والتأكيد وإعادة الإرسال وعرض المستخدم.
    │   │   └── rooms.py                 # عقود الغرف والدعوات والطلبات والاجتماع ورمز LiveKit.
    │   ├── services/                    # منطق الأعمال دون طبقة repositories.
    │   │   ├── __init__.py              # ملف فارغ.
    │   │   ├── identity.py              # إنشاء المستخدم الضيف والجلسة والتحقق من CSRF والخروج.
    │   │   ├── accounts.py              # التحقق من البيانات وإصدار رمز البريد وتفعيل الحساب.
    │   │   ├── captcha.py               # إصدار واستهلاك سؤال جمع رقمي بسيط.
    │   │   ├── passwords.py             # هاش bcrypt والتحقق — verify_password غير مستدعى من مسار عام.
    │   │   ├── mailer.py                # إرسال رمز التأكيد عبر smtplib وإرجاع MailResult بدون الرمز.
    │   │   ├── rooms.py                 # إنشاء الغرف والدعوات وطلبات الانضمام والصلاحيات.
    │   │   └── livekit.py               # إصدار JWT LiveKit وحالة media_provider.
    │   └── ws/                          # طبقة WebSocket في الذاكرة.
    │       ├── __init__.py              # تصدير hub وreset_hub.
    │       ├── hub.py                   # محور القنوات والحضور وأقران الوسائط والبث.
    │       ├── payloads.py              # بناء أحداث JSON للأعضاء والغرف والطلبات.
    │       ├── publish.py               # نشر أحداث الانضمام والقرار والإغلاق والحضور.
    │       └── router.py                # WS /api/ws/rooms/{id} و/api/ws/join-requests/{id}.
    └── tests/                           # اختبارات الخادم على SQLite في الذاكرة.
        ├── __init__.py                  # ملف فارغ.
        ├── conftest.py                  # عميل اختبار وبيئة test وتعطيل حد المعدل.
        ├── test_health.py               # صحة الخادم ونوع المحتوى و404.
        ├── test_config.py               # CORS وبيئة التطبيق وLiveKit والكوكيز الآمنة.
        ├── test_cors.py                 # رفض النجمة في الإنتاج ودمج PUBLIC_ORIGIN.
        ├── test_database_path.py        # إنشاء مجلد ملف SQLite وتجاهل :memory:.
        ├── test_security.py             # ترويسات أمنية وCSRF والخروج وحد المعدل وإخفاء docs.
        ├── test_rooms.py                # إنشاء الغرف والدعوات والطلبات والصلاحيات.
        ├── test_accounts.py             # التسجيل والتأكيد وإعادة الإرسال وعدم إرجاع الرمز.
        ├── test_mailer.py               # شرط SMTP والتشفير والفشل دون تسجيل الرمز.
        ├── test_livekit.py              # رفض الرمز لغير الأعضاء والاحتياط WebRTC.
        ├── test_websocket.py            # أحداث الغرفة والطلب والإشارات وإغلاق غير المالكين.
        ├── test_media_peers.py          # لقطة أقران الوسائط بعد join-media وleave-media.
        └── test_spa.py                  # تقديم index.html للأصول ومنع كسر API بلا dist.
```

مجلدات مذكورة في أمثلة عامة وغير موجودة هنا: `client/`، `server/`، `database/`، `docs/`، `public/`، `layouts/`، `routes/`، `contexts/`، `store/`، `assets/`، `types/`، `pages/auth/`، `dashboard/`، `account/`. التوجيه كله في `frontend/src/App.jsx`. لا توجد ملفات ترحيل Alembic منفصلة؛ الترحيل داخل `backend/app/database.py`.

---

## 2. التقنيات ولغات البرمجة وإصداراتها

| الجزء | التقنية | الإصدار | أين عُرّف |
| --- | --- | --- | --- |
| الواجهة | JavaScript JSX | — | `frontend/src/**` |
| الواجهة | React | ^18.3.1 / مقفول 18.3.1 | `frontend/package.json` |
| الواجهة | react-dom | ^18.3.1 / 18.3.1 | `frontend/package.json` |
| الواجهة | react-router-dom | ^6.28.1 / مقفول 6.30.6 | `frontend/package.json` |
| البناء | Vite | ^6.0.7 / مقفول 6.4.5 | `frontend/package.json` |
| البناء | @vitejs/plugin-react | ^4.3.4 / مقفول 4.7.0 | `frontend/package.json` |
| الخادم | Python | 3.11+ في README / 3.12 في Docker | `README.md`، `Dockerfile` |
| الخادم | FastAPI | 0.115.6 | `backend/requirements.txt` |
| الخادم | Uvicorn | 0.34.0 | `backend/requirements.txt` |
| البيانات | SQLAlchemy | 2.0.36 | `backend/requirements.txt` |
| البيانات | SQLite | مكتبة البيئة 3.40.1 | `DATABASE_URL` |
| التحقق | Pydantic | 2.10.4 | `backend/requirements.txt` |
| الإعداد | pydantic-settings | 2.7.0 | `backend/requirements.txt` |
| الإعداد | python-dotenv | 1.0.1 | `backend/requirements.txt` |
| الوسائط الاختيارية | PyJWT | 2.10.1 | `backend/requirements.txt` |
| كلمات المرور | bcrypt | 4.2.1 | `backend/requirements.txt` |
| الاختبار | pytest | 8.3.4 | `backend/requirements.txt` |
| الاختبار | httpx | 0.28.1 | `backend/requirements.txt` |
| اختبار الواجهة | node:test | مدمج في Node | `frontend/package.json` سكربت test |
| النشر | Docker | صورة node:20-alpine ثم python:3.12-slim | `Dockerfile` |

لا TypeScript في الواجهة. لا قاعدة غير SQLite في الإعداد الافتراضي. لا Redis ولا قائمة انتظار.

---

## 3. المكتبات والأطر المستخدمة ووظيفة كل منها

تمييز: «مثبّتة» من ملف الاعتماديات، «مستخدمة في الكود» إن وُجد استيراد أو استدعاء فعلي.

| المكتبة | مثبتة | مستخدمة في الكود | الوظيفة الفعلية |
| --- | --- | --- | --- |
| react / react-dom | نعم | نعم | بناء الصفحات وتركيبها في `#root`. |
| react-router-dom | نعم | نعم | مسارات الصفحات في `App.jsx`. |
| vite + plugin-react | نعم | نعم عند التشغيل/البناء | خادم التطوير والبناء. |
| livekit-client | نعم | نعم في `useLiveKit.js` فقط | عميل SFU عندما يختار الخادم `media_provider=livekit`. التثبيت لا يعني أن LiveKit يعمل؛ يحتاج أسراراً على الخادم. |
| WebRTC في المتصفح | أصلية | نعم في `useWebRtc.js` | المسار الافتراضي للصوت والصورة. |
| WebSocket في المتصفح | أصلية | نعم في `useRealtime.js` | الحضور وإشارات الند للند وحالة طلب الانضمام. |
| fetch | أصلية | نعم في `client.js` | كل REST. لا Axios. |
| FastAPI / Starlette | نعم | نعم | HTTP وWebSocket وCORS وترويسات. |
| SQLAlchemy | نعم | نعم | جداول وجلسات و`create_all`. |
| smtplib / email / ssl | قياسية | نعم في `mailer.py` | إرسال رمز التحقق. الإرسال الخارجي يحتاج SMTP مضبوطاً. |
| bcrypt | نعم | `hash_password` مستخدم؛ `verify_password` غير مستدعى من مسار عام | هاش كلمة المرور عند التسجيل. |
| PyJWT | نعم | نعم في `livekit.py` | رمز غرفة LiveKit للأعضاء فقط. |
| secrets / hashlib / hmac | قياسية | نعم | رموز الجلسة والدعوة وCAPTCHA ومقارنة آمنة. |
| anyio | يأتي مع Starlette | نعم في `ws/publish.py` | بث أحداث من سياق متزامن. |
| IBM Plex Sans Arabic | عبر Google Fonts في HTML | نعم إن وصل المتصفح للشبكة | خط الواجهة. لا ملفات خطوط محلية. |

غير موجود رغم شيوعه: Redux/Zustand، Tailwind، MUI، i18n library، Alembic، Celery، مكتبات بريد تجارية.

دوال/تصديرات معرّفة وغير مستدعاة من طبقات أعلى (تحقق بالبحث في المستودع): `verify_password`، `list_owned_rooms`، `read_csrf_token`، `mask_invite_code`، ودالة الواجهة `bootstrapSession`. المتغير `VITE_APP_NAME` في `.env.example` غير مقروء في الكود.

---

## 4. شرح الواجهات ومساراتها

التخطيط المشترك: `AppLayout` يغلّف كل المسارات. لا صفحات خارج هذا الغلاف. التصميم متجاوب في CSS عند 860px و480px. اختبار جهاز هاتف حقيقي: غير متحقق منه.

| الواجهة بالعربية | الاسم الإنجليزي للملف | مسار المتصفح | ملف المشروع | الحالة |
| --- | --- | --- | --- | --- |
| الرئيسية | HomePage | `/` | `frontend/src/pages/HomePage.jsx` | منفَّذة: صحة الخادم، ترحيب الجلسة، قائمة غرف العضوية، روابط إنشاء/انضمام/حساب. |
| إنشاء حساب | RegisterPage | `/register` | `frontend/src/pages/RegisterPage.jsx` | منفَّذة: نموذج + CAPTCHA ثم الانتقال للتأكيد. وصول البريد يعتمد على SMTP. |
| تأكيد البريد | VerifyEmailPage | `/verify-email` | `frontend/src/pages/VerifyEmailPage.jsx` | منفَّذة: رمز وإعادة إرسال. جلسة بعد النجاح. |
| تسجيل الدخول | LoginPage | `/login` | `frontend/src/pages/LoginPage.jsx` | غير مكتملة: نص «قريباً» بلا حقول وبلا API. |
| إنشاء غرفة | CreateRoomPage | `/create` | `frontend/src/pages/CreateRoomPage.jsx` | منفَّذة لضيف/مالك باسم العرض. لا تشترط حساباً موثَّقاً. |
| الانضمام بدعوة | JoinRoomPage | `/join` و `/join/:code` | `frontend/src/pages/JoinRoomPage.jsx` | منفَّذة: معاينة وإرسال طلب. |
| انتظار الموافقة | WaitingApprovalPage | `/waiting/:requestId` | `frontend/src/pages/WaitingApprovalPage.jsx` | منفَّذة: REST + WebSocket ثم تحويل للاجتماع عند القبول. |
| إدارة الغرفة | RoomManagePage | `/rooms/:roomId` | `frontend/src/pages/RoomManagePage.jsx` | منفَّذة للمالك: دعوات وطلبات وإغلاق. ليست لوحة حساب. |
| الاجتماع | MeetingPage | `/rooms/:roomId/meeting` | `frontend/src/pages/MeetingPage.jsx` | جزئية: منطق WebRTC/LiveKit موجود. مكالمة جهازين حقيقيين غير متحقق منها. لا مشاركة شاشة. |
| غير موجود | NotFoundPage | `*` | `frontend/src/pages/NotFoundPage.jsx` | منفَّذة كـ 404 بسيط. |
| إعادة توجيه | Navigate | `/home` | داخل `App.jsx` | تحويل إلى `/`. |

واجهات غير موجودة في المشروع: استعادة كلمة المرور، لوحة تحكم مستقلة، ملف شخصي، إعدادات الحساب، مركز إشعارات، لوحة إدارة منصة، شات نصي.

خدمات API التي تستدعيها الصفحات معرّفة في `frontend/src/api/client.js` وتتوافق مع مسارات القسم 5.

---

## 5. شرح الخادم الخلفي ومكوناته

نقطة التشغيل: `create_app()` في `backend/app/main.py` ثم `app = create_app()`. الأمر: `uvicorn app.main:app` من مجلد `backend`. عند الإقلاع يُستدعى `init_db()`.

لا Controllers منفصلة عن Routers. لا Repositories. الخدمات تستخدم SQLAlchemy مباشرة.

```text
main.py
  routers/* + ws/router.py
    deps.py
      services/*
        models/*
        security.py / errors.py / rate_limit.py / config.py
    schemas/*
  static_spa.py
```

المصادقة: كوكي HttpOnly اسمها الافتراضي `sc_session` (قيمة عشوائية؛ يُخزَّن SHA-256). CSRF: كوكي `sc_csrf` غير HttpOnly وترويسة `X-CSRF-Token` لطلبات التعديل. لا JWT للمستخدم. JWT فقط لرمز LiveKit. الضيف يُنشأ عبر `POST /api/session` أو ضمناً عند إنشاء غرفة أو طلب انضمام. بعد تأكيد البريد تُفتح جلسة على الحساب المفعّل.

التفويض داخل الغرفة فقط: مالك `owner` أو عضو `member` عبر `room_members`. لا دور مدير منصة.

WebSocket في ذاكرة عملية واحدة (`Hub`). لا يعمل عبر عدة نسخ خادم بدون طبقة نشر مشتركة.

### مسارات HTTP وWebSocket

| Method | Endpoint | الوظيفة | ملف التنفيذ |
| --- | --- | --- | --- |
| GET | `/api/health` | اتصال القاعدة ومزوّد الوسائط | `backend/app/routers/health.py` |
| GET | `/api/session` | قراءة الجلسة أو 401 | `backend/app/routers/session.py` |
| POST | `/api/session` | جلسة ضيف باسم العرض | `session.py` |
| DELETE | `/api/session` | إبطال الجلسة والكوكيز | `session.py` |
| GET | `/api/accounts/captcha` | سؤال تحقق حسابي | `backend/app/routers/accounts.py` |
| POST | `/api/accounts/register` | حساب معلّق وإرسال رمز إن أمكن | `accounts.py` |
| POST | `/api/accounts/verify-email` | تفعيل وفتح جلسة | `accounts.py` |
| POST | `/api/accounts/resend-verification` | إبطال الرمز السابق وإصدار جديد | `accounts.py` |
| POST | `/api/rooms` | غرفة + عضوية مالك + دعوة أولية | `backend/app/routers/rooms.py` |
| GET | `/api/rooms` | غرف عضوية المستخدم | `rooms.py` |
| GET | `/api/rooms/{id}` | تفاصيل؛ الدعوات والطلبات للمالك | `rooms.py` |
| POST | `/api/rooms/{id}/close` | إغلاق الغرفة | `rooms.py` |
| POST | `/api/rooms/{id}/invitations` | دعوة جديدة؛ الرمز الكامل مرة واحدة | `rooms.py` |
| POST | `/api/invitations/{id}/revoke` | إبطال دعوة | `rooms.py` |
| GET | `/api/invites/{code}` | معاينة عامة للدعوة | `rooms.py` |
| POST | `/api/join-requests` | طلب انضمام معلّق | `rooms.py` |
| GET | `/api/join-requests/{id}` | حالة الطلب لمقدمه | `rooms.py` |
| POST | `/api/join-requests/{id}/decision` | قبول أو رفض من المالك | `rooms.py` |
| GET | `/api/rooms/{id}/meeting` | بوابة الاجتماع والوسائط | `rooms.py` |
| POST | `/api/rooms/{id}/livekit-token` | JWT إن LiveKit مضبوط وعضوية نشطة وإلا 503 | `rooms.py` |
| WS | `/api/ws/rooms/{id}` | حضور وإشارات وسائط للأعضاء | `backend/app/ws/router.py` |
| WS | `/api/ws/join-requests/{id}` | حالة الطلب لمقدمه | `ws/router.py` |
| GET | `/{path}` غير `/api` | SPA من `frontend/dist` | `backend/app/static_spa.py` |

لا مسارات login أو reset-password أو رسائل نصية أو ملف شخصي.

---

## 6. قاعدة البيانات والجداول والعلاقات

النوع: SQLite عبر SQLAlchemy. العنوان الافتراضي `sqlite:///./securechat.db` نسبي لمسار تشغيل uvicorn (عادة `backend/securechat.db`).

توجد نسختان على القرص:

1. `backend/securechat.db` — المخطط الحالي بما فيه جداول الحساب. هذه التي يحدّثها الخادم عند التشغيل من `backend/`.
2. `./securechat.db` في الجذر — مخطط أقدم: `users` بلا أعمدة البريد، ولا جدولا `captcha_challenges` و`email_verifications`. بقايا مسار تشغيل قديم.

لا تُعرض في هذا الملف كلمات المرور أو رموز التحقق أو بيانات المستخدمين.

الإنشاء: `Base.metadata.create_all` ثم جدول `schema_migrations` بإصداري `0001_rooms_invites_join_requests` و`0002_accounts_email_verification`. أعمدة الحساب تُضاف بـ `ALTER TABLE` إن نقصت. `PRAGMA foreign_keys=ON` و`journal_mode=WAL`.

### الجداول في المخطط الحالي

**users:** id PK، display_name، created_at، first_name، last_name، email، email_normalized (فهرس فريد)، password_hash، email_verified_at، terms_accepted_at، account_status (`guest` / `pending` / `active`).

**sessions:** id، user_id FK CASCADE، token_hash فريد، csrf_token_hash، created_at، expires_at، last_seen_at.

**captcha_challenges:** id، answer_hash، expires_at، created_at، consumed. بلا مفتاح أجنبي.

**email_verifications:** id، user_id FK CASCADE، email_normalized، code_hash، purpose (افتراضي `signup`)، expires_at، attempts، max_attempts، used_at، created_at.

**rooms:** id، name، description، owner_id FK RESTRICT، status (`active` / `closed`)، max_participants، allow_guest_requests، created_at.

**room_members:** id، room_id وuser_id FK CASCADE، قيد فريد (room_id, user_id)، role (`owner` / `member`)، status (`active`)، display_name، joined_at.

**invitations:** id، room_id CASCADE، created_by RESTRICT، code_hash فريد، code_prefix، status (`active` / `revoked` / `expired` / `exhausted`)، max_uses، use_count، expires_at، created_at، revoked_at.

**join_requests:** id، room_id CASCADE، user_id CASCADE، invitation_id SET NULL، قيد فريد (room_id, user_id)، display_name، status (`pending` / `approved` / `rejected` / `cancelled`)، created_at، decided_at، decided_by SET NULL.

**schema_migrations:** version PK، applied_at. للتتبع بعد الإدراج؛ لا يُقرأ في منطق الأعمال.

كل جداول النماذج مستخدمة في الكود. لا طبقة `database/` منفصلة عن ملفات SQLite هذه.

### علاقات نصية

```text
users 1--* sessions
users 1--* email_verifications
users 1--* rooms                 عبر owner_id
users 1--* room_members
users 1--* join_requests         مقدّم الطلب
users 1--* join_requests         المراجع عبر decided_by
users 1--* invitations           عبر created_by
rooms 1--* room_members
rooms 1--* invitations
rooms 1--* join_requests
invitations 1--* join_requests   اختياري
captcha_challenges               مستقل
schema_migrations                مستقل
```

---

## 7. إنشاء الحساب والتحقق من البريد

المنفَّذ:

1. الواجهة تجلب CAPTCHA: جمع رقمين، صلاحية 600 ثانية، الإجابة تُخزَّن هاشاً وتُستهلك مرة (`backend/app/services/captcha.py`).
2. الخادم يتحقق من الأسماء والبريد وكلمة المرور (8 أحرف على الأقل، بلا مسافات، صنفان على الأقل) وموافقة الشروط (`backend/app/services/accounts.py`).
3. كلمة المرور تُخزَّن بـ bcrypt. الرمز رقم من 6 خانات يُهاش ولا يُرجع في JSON ولا يُكتب في سجلات الإنتاج.
4. البريد الموجود غير الموثَّق يُحدَّث كحساب معلّق. الموثَّق يعيد تعارضاً.
5. صلاحية الرمز من `EMAIL_VERIFICATION_TTL_SECONDS` (افتراضي 60 ثانية). إعادة الإرسال تبطل الرموز السابقة غير المستخدمة لنفس المستخدم.
6. النجاح يضع `email_verified_at` و`account_status=active` ثم ينشئ جلسة كوكي.
7. الإرسال عبر `smtplib` في `mailer.py`. الشرط: `SMTP_HOST` وعنوان مرسل (`SMTP_FROM` أو `SMTP_FROM_EMAIL`).

غير مكتمل أو خارجي:

- تسجيل الدخول بكلمة المرور غير منفَّذ.
- استعادة كلمة المرور غير منفَّذة.
- وصول رسالة إلى صندوق بريد حقيقي غير متحقق منه في هذه البيئة إن لم تُضبط متغيرات SMTP على الخادم. ظهور رسالة «إرسال البريد غير مضبوط» يعني أن الشرط أعلاه غير متحقق، وليس عطل توليد الرمز.

لا تُدرج في هذا الملف قيم SMTP أو كلمات مرور التطبيقات.

---

## 8. الغرف والدعوات والموافقة على الانضمام

| الخطوة | الواجهة | API | التخزين |
| --- | --- | --- | --- |
| إنشاء الغرفة | CreateRoomPage | `POST /api/rooms` | `rooms` + عضو مالك في `room_members` |
| هوية المالك | اسم العرض | `ensure_session_user` | `users` + `sessions` إن لزم |
| الدعوة الأولية | ضمن الإنشاء | نفس الطلب | `invitations`؛ الرمز الكامل مرة في الاستجابة |
| نسخ الرابط | RoomManagePage | — | `{origin}/join/{code}` في الواجهة |
| فتح الرابط | JoinRoomPage | `GET /api/invites/{code}` | معاينة بلا أعضاء |
| طلب الانضمام | JoinRoomPage | `POST /api/join-requests` | `join_requests` بحالة pending |
| إشعار المالك | RoomManagePage | WebSocket `join_request` | قناة الغرفة للمالك فقط |
| قبول أو رفض | RoomManagePage | `POST .../decision` | قبول يضيف `room_members` |
| الدخول بعد الموافقة | WaitingApprovalPage أو اجتماع | `require_room_access` | عضوية نشطة شرط الاجتماع وWS |
| إغلاق | RoomManagePage | `POST .../close` | `rooms.status=closed` ويُغلق WS لغير المالك |

لا مسار يزيل العضوية عند المغادرة. الإغلاق لا يحذف السجلات. لا طرد أعضاء في الكود.

---

## 9. الرسائل والاتصال الفوري

لا يوجد نظام رسائل نصية أو شات. الاسم SecureChat في هذا الإصدار يعني غرف اجتماع خاصة وليس محادثة نصية.

الاتصال الفوري عبر WebSocket:

- قناة الغرفة: حضور، تحديث أعضاء، طلبات للمالك، إغلاق، إشارات وسائط.
- قناة الطلب: تحديث حالة طلب الانضمام لمقدمه فقط.
- أحداث إدارية عبر socket (`approve` / `reject`) مرفوضة؛ القرار عبر REST فقط.
- إعادة اتصال الواجهة أسّية مع ping كل 25 ثانية.

اختبارات التوجيه في `backend/tests/test_websocket.py`. لا إشعارات بريد لأحداث الغرفة. لا مركز إشعارات في الواجهة.

---

## 10. WebRTC وLiveKit

كلا المسارين موجودان في الكود. المسار الافتراضي WebRTC لأن `WEBRTC_FALLBACK=true` ما لم تكتمل بيانات LiveKit بعنوان غير محلي يصل إليه المتصفح.

WebRTC (`frontend/src/hooks/useWebRtc.js` + إشارات `ws/router.py`):

- `getUserMedia` للكاميرا والميكروفون.
- `RTCPeerConnection` مع STUN عام `stun:stun.l.google.com:19302`.
- لا TURN في المشروع. شبكات NAT المتماثلة قد تفشل — غير متحقق منه ميدانياً.
- إجراءات الإشارة: `join-media`، `leave-media`، `offer`، `answer`، `ice`، `media-state`.

LiveKit (`backend/app/services/livekit.py` + `frontend/src/hooks/useLiveKit.js`):

- يحتاج `LIVEKIT_URL` و`LIVEKIT_API_KEY` و`LIVEKIT_API_SECRET` على الخادم فقط.
- الرمز لا يُصدر إلا بعد عضوية نشطة وغرفة غير مغلقة.
- عنوان loopback يدفع الاحتياط إلى WebRTC حتى لا يُعطى المتصفح عنواناً لا يصل إليه.

مشاركة الشاشة والتسجيل: غير منفَّذين. ظهور بلاطة محلية لا يثبت نجاح مكالمة بين طرفين. اختبار جهازين لعدة دقائق: غير متحقق منه في بيئة بلا كاميرا وميكروفون.

---

## 11. التصميم والتجاوب

الملف الوحيد للتصميم: `frontend/src/styles/index.css`.

- اتجاه RTL من `html { direction: rtl }` و`index.html`.
- ألوان داكنة: خلفية `#07111f`، نص `#f4f7fb`، تمييز أزرق، نجاح أخضر، تحذير أصفر، خطر أحمر.
- الخط من Google Fonts مع احتياطي محلي في المتصفح.
- لا قائمة جانبية ولا نوافذ modal؛ ترويسة أفقية وبانرات.
- نقاط قطع 860px و480px: عمود واحد، أزرار أعرض، شبكة فيديو عمودية على الشاشات الضيقة.
- شعار الترويسة حرف S بـ CSS. لا مجلد `assets` ولا favicon في المستودع.

تجاوب الهاتف موصوف في CSS. لم يُختبر على جهاز حقيقي هنا: غير متحقق منه.

---

## 12. طريقة التشغيل والاختبارات

المتطلبات الموثقة: Python 3.11 أو أحدث، Node.js 18 أو أحدث، npm.

تطوير منفصل:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd frontend
npm install
npm run dev
```

معاً: `./start.sh` — منفذ المعاينة 5173 مع بروكسي `/api` إلى 8000.

إنتاج: بناء الواجهة ثم `APP_ENV=production ./start-production.sh`. Docker يستخدم `FRONTEND_DIST_DIR=/app/frontend/dist`.

اختبارات الخادم تستخدم SQLite في الذاكرة ولا تكتب في ملف المشروع:

```bash
cd backend
pytest
```

اختبارات الواجهة الحالية تغطي تخطيط الشبكة فقط:

```bash
cd frontend
npm test
```

جرد الاختبارات على القرص: 83 دالة `test_*` تحت `backend/tests` و4 اختبارات في `meetingLayout.test.js`. نتيجة آخر تشغيل pytest في هذه الجلسة: غير متحقق منه (لم يُنفَّذ هنا حتى لا تُخلط مهمة التوثيق مع تغيير حالة التشغيل).

خدمات خارجية: SQLite محلي إلزامي. SMTP لإرسال رمز البريد فقط. LiveKit اختياري. STUN عام لمسار WebRTC. أسرار البيئة لا تُنسخ إلى الواجهة ولا إلى هذا الملف.

نشر Render من `render.yaml` على خطة مجانية بلا قرص دائم: ملف SQLite يُفقد عند إعادة التشغيل ما لم يُضف Disk خارج هذا المستودع.

---

## 13. حالة اكتمال الوظائف والمشكلات المعروفة

علامة مكتمل تتطلب تنفيذاً في الكود واختباراً ملائماً موجوداً. ظهور الصفحة وحده لا يكفي.

| النظام | الحالة | ما يدعم الحكم |
| --- | --- | --- |
| إنشاء الحساب | جزئي مكتمل في الخادم/الواجهة | `test_accounts.py`؛ لا اختبار متصفح E2E |
| التحقق من البريد | جزئي | تحقق الرمز مختبر مع mock؛ SMTP الحقيقي غير متحقق منه |
| تسجيل الدخول | غير منفَّذ | `LoginPage` نائب؛ لا مسار API |
| استعادة كلمة المرور | غير منفَّذ | لا ملفات |
| لوحة التحكم | جزئي | قائمة غرف في الرئيسية فقط |
| الغرف | منفَّذ ومختبر | `test_rooms.py` |
| الدعوات | منفَّذ ومختبر | إنشاء وانتهاء وحد وإبطال |
| الموافقة على الانضمام | منفَّذ ومختبر | REST وWebSocket |
| الرسائل النصية | غير منفَّذ | لا شات |
| الصوت | جزئي | إشارة WS مختبرة؛ مكالمة أجهزة غير متحقق منها |
| الفيديو | جزئي | نفس الصوت؛ تخطيط الشبكة مختبر في `meetingLayout.test.js` |
| الإعدادات | غير منفَّذ | لا صفحة |
| الإشعارات | جزئي | أحداث WebSocket بلا مركز إشعارات |

### مشكلات مصنّفة

حرجة: SQLite على استضافة بلا قرص دائم؛ محور WebSocket داخل عملية واحدة لا يتزامن بين عدة نسخ؛ ملفّا قاعدة بمخططين مختلفين إن شُغّل الخادم من الجذر بدل `backend/`.

عالية: SMTP قد يكون غير مضبوط في بيئة التطوير؛ لا TURN؛ لا تسجيل دخول بعد سقوط الكوكي؛ الرمز الكامل للدعوة يظهر مرة واحدة ثم لا يُستعاد؛ حد المعدل في ذاكرة العملية.

متوسطة: دوال غير مستخدمة مذكورة في القسم 3؛ CAPTCHA حسابي ضعيف أمام بوت جاد؛ لا طرد أعضاء؛ `package-lock.json` متعارض مع `.gitignore`.

منخفضة: قيد فريد مكرر على `email_verifications.id` مع المفتاح الأساسي؛ لا favicon؛ اعتماد `livekit-client` يبقى حتى عندما المسار WebRTC.

أمني دفاعي موجود في الكود ومختبر جزئياً في `test_security.py`: كوكيز HttpOnly، CSRF، هاش الرموز والدعوات، bcrypt، إخفاء رمز البريد من API، تقييد CORS في الإنتاج، إخفاء OpenAPI في الإنتاج. لا مفاتيح في الواجهة.

---

## 14. ما ليس في هذا المشروع

لا تختر هيكل `client/` أو `server/` أو `docs/` عند إعادة التنظيم بناءً على هذا الملف ما لم تُنشأ لاحقاً بقرار صريح. الهيكل المعتمد الآن هو `frontend/` و`backend/` مع تشغيل مشترك عبر `start.sh` أو Docker.

هذا التوثيق يطابق الملفات على القرص وقت إنشائه. أي إضافة لاحقة لصفحات أو جداول تجعل الفقرات المعنية بحاجة لمطابقة جديدة.

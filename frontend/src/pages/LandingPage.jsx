import { Link } from "react-router-dom";
import ActionButton from "../components/ActionButton";
import { useSession } from "../context/SessionContext";

const FEATURES = [
  {
    title: "اجتماعات صوت وصورة",
    body: "يتصل الأعضاء المعتمدون داخل الغرفة عبر WebRTC للصوت والصورة دون وسيط خارجي ظاهر للمستخدم.",
  },
  {
    title: "غرف خاصة",
    body: "تُنشأ الغرفة في الخادم باسم ووصف وحدّ مشاركين. الرابط العام لا يفتح الاجتماع مباشرة.",
  },
  {
    title: "دعوات وطلبات الانضمام",
    body: "دعوة برمز فريد وصلاحية محدودة. يبقى الطلب معلقاً حتى يقبله مالك الغرفة.",
  },
  {
    title: "محادثة نصية",
    body: "رسائل الغرفة تُحفظ للأعضاء المعتمدين وتُعرض في الاجتماع وصفحة الغرفة.",
  },
  {
    title: "مشاركة الشاشة",
    body: "يمكن بدء مشاركة الشاشة من المتصفح عبر اتصال WebRTC الحالي، مع الإبقاء على الصوت والكاميرا.",
  },
  {
    title: "الإشعارات",
    body: "تنبيهات لطلبات الانضمام والرسائل وقرارات الدعوة، مع تعليم المقروء من صفحة الإشعارات.",
  },
  {
    title: "إدارة المشاركين",
    body: "المالك يرى الأعضاء والدعوات والطلبات المعلقة، ويمكنه إغلاق الغرفة أو إبطال دعوة.",
  },
];

const STEPS = [
  {
    step: "1",
    title: "أنشئ حساباً وأكّد بريدك",
    body: "التسجيل يطلب بياناتك وكلمة مرور وتحققاً بصرياً. الجلسة لا تُفتح قبل رمز التأكيد.",
  },
  {
    step: "2",
    title: "أنشئ غرفة أو استقبل دعوة",
    body: "من لوحة التحكم تنشئ غرفة خاصة أو تفتح رابط دعوة أرسله إليك المالك.",
  },
  {
    step: "3",
    title: "الموافقة عند الحاجة",
    body: "طلب الانضمام يبقى معلقاً حتى يقبله المالك. العضوية المعتمدة وحدها تفتح الغرفة.",
  },
  {
    step: "4",
    title: "ابدأ الاجتماع",
    body: "بعد القبول تدخل الاجتماع للصوت والصورة والمحادثة ومشاركة الشاشة مع الأعضاء الآخرين.",
  },
];

const SECURITY = [
  {
    title: "غرف خاصة",
    body: "لا يوجد دليل عام للغرف. الوصول عبر عضوية أو دعوة مخزّنة في الخادم.",
  },
  {
    title: "دعوات مقيّدة",
    body: "لكل دعوة رمز وعدد استخدامات اختياري وتاريخ انتهاء، ويمكن إبطالها من المالك.",
  },
  {
    title: "قبول المشاركين",
    body: "المالك يوافق أو يرفض طلبات الانضمام قبل دخول واجهة الغرفة أو الاجتماع.",
  },
  {
    title: "حماية الحساب",
    body: "كلمة المرور تُخزَّن بعد تجزئة، والتأكيد عبر البريد، والجلسة عبر كوكي HTTP-only مع رمز CSRF.",
  },
];

export default function LandingPage() {
  const { user } = useSession();

  return (
    <div className="landing-page">
      <section className="landing-hero" id="top">
        <div className="container landing-hero-grid">
          <div className="landing-hero-copy reveal">
            <p className="kicker">منصة الغرف الخاصة</p>
            <h1>اجتماعات صوت وصورة داخل غرف لا يدخلها إلا من توافقون عليه</h1>
            <p>
              SecureChat منصة عربية لإنشاء غرف خاصة، إرسال دعوات مقيّدة، الموافقة على طلبات
              الانضمام، ثم التواصل بالصوت والصورة والمحادثة النصية بين الأعضاء المعتمدين.
            </p>
            <div className="hero-actions">
              {user ? (
                <Link to="/app">
                  <ActionButton>الانتقال إلى لوحة التحكم</ActionButton>
                </Link>
              ) : (
                <>
                  <Link to="/register">
                    <ActionButton>ابدأ الآن</ActionButton>
                  </Link>
                  <Link to="/login">
                    <ActionButton variant="secondary">تسجيل الدخول</ActionButton>
                  </Link>
                </>
              )}
            </div>
          </div>
          <div className="meeting-preview reveal" aria-hidden="true">
            <div className="preview-top">
              <span className="preview-dot" />
              <span>غرفة الفريق — مباشر</span>
              <span className="status-chip">03:12</span>
            </div>
            <div className="preview-grid">
              <article className="preview-tile local">
                <div className="preview-avatar">أ</div>
                <span>أنت</span>
              </article>
              <article className="preview-tile">
                <div className="preview-avatar">س</div>
                <span>سارة</span>
              </article>
              <article className="preview-tile">
                <div className="preview-avatar">خ</div>
                <span>خالد</span>
              </article>
              <article className="preview-tile screen">
                <div className="preview-screen" />
                <span>شاشة ليلى</span>
              </article>
            </div>
            <div className="preview-bar">
              <span>صوت</span>
              <span>كاميرا</span>
              <span>شاشة</span>
              <span>محادثة</span>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section" id="features">
        <div className="container">
          <p className="kicker">المميزات</p>
          <h2>ما الذي تقدمه المنصة اليوم</h2>
          <p className="section-lead">
            البطاقات التالية تعكس وظائف منفّذة في المنتج الحالي، وليست وعوداً مستقبلية.
          </p>
          <div className="feature-grid">
            {FEATURES.map((item) => (
              <article key={item.title} className="feature-card">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section" id="how">
        <div className="container">
          <p className="kicker">كيف تعمل المنصة؟</p>
          <h2>أربع خطوات حتى الاجتماع</h2>
          <div className="steps-grid">
            {STEPS.map((item) => (
              <article key={item.step} className="step-card">
                <span className="step-index">{item.step}</span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section" id="security">
        <div className="container">
          <p className="kicker">الأمان والخصوصية</p>
          <h2>التحكم يبقى لدى مالك الغرفة</h2>
          <div className="feature-grid security-grid">
            {SECURITY.map((item) => (
              <article key={item.title} className="feature-card">
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-cta" id="cta">
        <div className="container cta-card">
          <h2>ابدأ غرفتك الخاصة خلال دقائق</h2>
          <p>
            أنشئ حساباً، أكّد بريدك، ثم أنشئ غرفة أو انضم عبر دعوة. لن يُفتح الاجتماع قبل العضوية المعتمدة.
          </p>
          <div className="hero-actions">
            {user ? (
              <Link to="/app">
                <ActionButton>لوحة التحكم</ActionButton>
              </Link>
            ) : (
              <>
                <Link to="/register">
                  <ActionButton>إنشاء حساب</ActionButton>
                </Link>
                <Link to="/login">
                  <ActionButton variant="secondary">تسجيل الدخول</ActionButton>
                </Link>
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

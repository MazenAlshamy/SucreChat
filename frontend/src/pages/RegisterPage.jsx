import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchCaptcha, registerAccount } from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import TextField from "../components/TextField";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [captcha, setCaptcha] = useState(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadCaptcha() {
    try {
      const data = await fetchCaptcha();
      setCaptcha(data);
      setCaptchaAnswer("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadCaptcha();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("كلمتا المرور غير متطابقتين");
      return;
    }
    if (!termsAccepted) {
      setError("يلزم الموافقة على الشروط");
      return;
    }
    setLoading(true);
    try {
      const result = await registerAccount({
        first_name: firstName,
        last_name: lastName,
        email,
        password,
        terms_accepted: true,
        captcha_id: captcha?.captcha_id || "",
        captcha_answer: captchaAnswer,
      });
      navigate("/verify-email", {
        state: { email: result.email, message: result.message, mailSent: result.mail_sent },
      });
    } catch (err) {
      setError(err.message);
      loadCaptcha();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card auth-card">
      <PageHeader
        kicker="حساب جديد"
        title="إنشاء حساب"
        description="أدخل بياناتك ثم أكّد بريدك برمز يُرسل إليك. لن تُفتح جلسة قبل التأكيد."
      />
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <TextField
            id="firstName"
            label="الاسم الأول"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            autoComplete="given-name"
            required
          />
          <TextField
            id="lastName"
            label="اسم العائلة"
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            autoComplete="family-name"
            required
          />
        </div>
        <TextField
          id="email"
          label="البريد الإلكتروني"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
        <TextField
          id="password"
          label="كلمة المرور"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          required
        />
        <TextField
          id="confirmPassword"
          label="تأكيد كلمة المرور"
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          autoComplete="new-password"
          required
        />
        <p className="small muted">ثمانية أحرف على الأقل، مع حرف ورقم أو رمز. لا مسافات.</p>
        <label className="check-row">
          <input
            type="checkbox"
            checked={termsAccepted}
            onChange={(event) => setTermsAccepted(event.target.checked)}
          />
          <span>أوافق على شروط الاستخدام</span>
        </label>
        <div className="captcha-box">
          <p className="small">{captcha?.question || "جارٍ تحميل سؤال التحقق"}</p>
          <TextField
            id="captchaAnswer"
            label="إجابة التحقق"
            value={captchaAnswer}
            onChange={(event) => setCaptchaAnswer(event.target.value)}
            inputMode="numeric"
            required
          />
        </div>
        <div className="form-actions">
          <ActionButton type="submit" disabled={loading || !captcha}>
            {loading ? "جارٍ الإنشاء" : "إنشاء الحساب"}
          </ActionButton>
          <ActionButton variant="secondary" onClick={() => navigate("/")}>
            الصفحة الرئيسية
          </ActionButton>
        </div>
      </form>
      <p className="small">
        لديك حساب؟ <Link to="/login">تسجيل الدخول</Link>
      </p>
      {error ? <StatusBanner title="تعذر إنشاء الحساب">{error}</StatusBanner> : null}
    </div>
  );
}

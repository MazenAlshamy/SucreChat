import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { fetchCaptcha, resendVerification, verifyEmail } from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import TextField from "../components/TextField";
import { useSession } from "../context/SessionContext";

export default function VerifyEmailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { refreshSession } = useSession();
  const [email, setEmail] = useState(location.state?.email || "");
  const [code, setCode] = useState("");
  const [message, setMessage] = useState(location.state?.message || "");
  const [mailSent, setMailSent] = useState(Boolean(location.state?.mailSent));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [captcha, setCaptcha] = useState(null);
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [showResend, setShowResend] = useState(false);

  useEffect(() => {
    fetchCaptcha()
      .then(setCaptcha)
      .catch(() => {});
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyEmail({ email, code });
      await refreshSession();
      navigate("/app", { replace: true, state: { justVerified: true } });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleResend(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await resendVerification({
        email,
        captcha_id: captcha?.captcha_id || "",
        captcha_answer: captchaAnswer,
      });
      setMessage(result.message);
      setMailSent(Boolean(result.mail_sent));
      setShowResend(false);
      setCaptchaAnswer("");
      const next = await fetchCaptcha();
      setCaptcha(next);
    } catch (err) {
      setError(err.message);
      fetchCaptcha().then(setCaptcha).catch(() => {});
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card auth-card">
      <PageHeader
        kicker="تأكيد البريد"
        title="أدخل رمز التأكيد"
        description="الرمز صالح لدقيقة واحدة. بعد التأكيد تُفتح جلستك وتُعرض اسمك في الرئيسية."
      />
      {message ? (
        <StatusBanner tone={mailSent ? "success" : "warning"} title="الحساب بانتظار التأكيد">
          {message}
        </StatusBanner>
      ) : null}
      <form onSubmit={handleSubmit}>
        <TextField
          id="verifyEmail"
          label="البريد الإلكتروني"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
        <TextField
          id="verifyCode"
          label="رمز التأكيد"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          inputMode="numeric"
          maxLength={6}
          autoComplete="one-time-code"
          required
        />
        <div className="form-actions">
          <ActionButton type="submit" disabled={loading}>
            {loading ? "جارٍ التحقق" : "تأكيد البريد"}
          </ActionButton>
          <ActionButton variant="ghost" onClick={() => setShowResend((value) => !value)}>
            إعادة إرسال الرمز
          </ActionButton>
        </div>
      </form>
      {showResend ? (
        <form onSubmit={handleResend}>
          <p className="small">{captcha?.question || "جارٍ تحميل سؤال التحقق"}</p>
          <TextField
            id="resendCaptcha"
            label="إجابة التحقق لإعادة الإرسال"
            value={captchaAnswer}
            onChange={(event) => setCaptchaAnswer(event.target.value)}
            required
          />
          <ActionButton type="submit" disabled={loading || !captcha}>
            إرسال رمز جديد
          </ActionButton>
        </form>
      ) : null}
      <p className="small">
        <Link to="/register">العودة لإنشاء الحساب</Link>
        {" · "}
        <Link to="/login">تسجيل الدخول</Link>
      </p>
      {error ? <StatusBanner title="تعذر التأكيد">{error}</StatusBanner> : null}
    </div>
  );
}

import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { loginAccount } from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import TextField from "../components/TextField";
import { useSession } from "../context/SessionContext";
import { safeReturnPath } from "../utils/navigation";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { refreshSession, user, ready } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const nextPath = safeReturnPath(location.state?.from);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await loginAccount({ email, password });
      await refreshSession();
      navigate(nextPath, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (ready && user) {
    return (
      <div className="card auth-card">
        <PageHeader
          kicker="جلسة نشطة"
          title={`مرحباً ${user.display_name}`}
          description="أنت مسجّل الدخول بالفعل. يمكنك الانتقال إلى لوحة التحكم أو العودة إلى الصفحة الرئيسية."
        />
        <div className="form-actions">
          <ActionButton onClick={() => navigate(nextPath, { replace: true })}>لوحة التحكم</ActionButton>
          <ActionButton variant="secondary" onClick={() => navigate("/")}>
            الصفحة الرئيسية
          </ActionButton>
        </div>
      </div>
    );
  }

  return (
    <div className="card auth-card">
      <PageHeader
        kicker="تسجيل الدخول"
        title="مرحباً بعودتك"
        description="أدخل بريدك وكلمة المرور لحساب مؤكد. فتح الموقع وحده لا يعدّ دخولاً."
      />
      <form onSubmit={handleSubmit}>
        <TextField
          id="loginEmail"
          label="البريد الإلكتروني"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
        <TextField
          id="loginPassword"
          label="كلمة المرور"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
        <div className="form-actions">
          <ActionButton type="submit" disabled={loading}>
            {loading ? "جارٍ الدخول" : "دخول"}
          </ActionButton>
          <ActionButton variant="secondary" onClick={() => navigate("/register")}>
            إنشاء حساب
          </ActionButton>
        </div>
      </form>
      <p className="small">
        لم تؤكد بريدك؟ <Link to="/verify-email">تأكيد البريد</Link>
        {" · "}
        <Link to="/">الصفحة الرئيسية</Link>
      </p>
      {error ? <StatusBanner title="تعذر تسجيل الدخول">{error}</StatusBanner> : null}
    </div>
  );
}

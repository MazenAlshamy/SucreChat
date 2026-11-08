import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { previewInvite, submitJoinRequest } from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import TextField from "../components/TextField";
import { useSession } from "../context/SessionContext";

export default function JoinRoomPage() {
  const { code: codeFromUrl } = useParams();
  const navigate = useNavigate();
  const { refreshSession } = useSession();
  const [code, setCode] = useState(codeFromUrl || "");
  const [displayName, setDisplayName] = useState("");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (codeFromUrl) {
      setCode(codeFromUrl);
    }
  }, [codeFromUrl]);

  useEffect(() => {
    if (!code) {
      setPreview(null);
      return undefined;
    }
    let cancelled = false;
    previewInvite(code)
      .then((data) => {
        if (!cancelled) {
          setPreview(data);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setPreview(null);
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await submitJoinRequest({ code, display_name: displayName });
      await refreshSession();
      if (result.status === "approved") {
        navigate(`/rooms/${result.room_id}/meeting`);
        return;
      }
      navigate(`/waiting/${result.id}`);
    } catch (err) {
      const payload = err.payload;
      if (payload?.status === "approved" && payload?.room_id) {
        navigate(`/rooms/${payload.room_id}/meeting`);
        return;
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <PageHeader
        kicker="دعوة خاصة"
        title="الانضمام عبر رابط"
        description="يتحقق الخادم من صلاحية الدعوة عند فتح الصفحة وعند إرسال الطلب. رابط الدعوة لا يمنح دخولاً مباشراً."
      />
      {preview?.valid ? (
        <div className="notice">
          <strong>{preview.room_name}</strong>
          <p className="small" style={{ marginBottom: 0 }}>
            {preview.description || "غرفة خاصة بانتظار موافقة المالك."}
          </p>
        </div>
      ) : null}
      {preview && !preview.valid ? (
        <StatusBanner title="الدعوة غير صالحة">{preview.reason}</StatusBanner>
      ) : null}
      <form onSubmit={handleSubmit}>
        {!codeFromUrl ? (
          <TextField
            id="inviteCode"
            label="رمز الدعوة"
            value={code}
            onChange={(event) => setCode(event.target.value.trim())}
            placeholder="الصق رمز الدعوة هنا"
            required
          />
        ) : null}
        <TextField
          id="displayName"
          label="اسم العرض"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder="سارة"
          required
        />
        <div className="form-actions">
          <ActionButton type="submit" disabled={loading || (preview && !preview.valid)}>
            {loading ? "جارٍ الإرسال" : "طلب الانضمام"}
          </ActionButton>
          <Link to="/">
            <ActionButton variant="ghost">العودة</ActionButton>
          </Link>
        </div>
      </form>
      {error ? <StatusBanner title="تعذر إرسال الطلب">{error}</StatusBanner> : null}
    </div>
  );
}

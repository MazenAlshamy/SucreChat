import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRoom } from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import TextField from "../components/TextField";

export default function CreateRoomPage() {
  const navigate = useNavigate();
  const [roomName, setRoomName] = useState("");
  const [description, setDescription] = useState("");
  const [hostName, setHostName] = useState("");
  const [maxParticipants, setMaxParticipants] = useState(8);
  const [expiresInHours, setExpiresInHours] = useState(24);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await createRoom({
        name: roomName,
        description: description || null,
        max_participants: Number(maxParticipants),
        display_name: hostName,
        allow_guest_requests: true,
        invite_max_uses: null,
        invite_expires_in_hours: Number(expiresInHours) || 24,
      });
      navigate(`/rooms/${result.room.id}`, {
        state: { freshInviteCode: result.invitations[0]?.code || "" },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <PageHeader
        kicker="غرفة خاصة"
        title="إنشاء غرفة"
        description="تُحفظ الغرفة في الخادم وتُنشأ دعوة أولية صالحة ليوم واحد. اسم العرض يرتبط بجلسة آمنة وليس هوية نهائية للحساب."
      />
      <form onSubmit={handleSubmit}>
        <TextField
          id="roomName"
          label="اسم الغرفة"
          value={roomName}
          onChange={(event) => setRoomName(event.target.value)}
          placeholder="اجتماع الفريق الأمني"
          required
        />
        <TextField
          id="description"
          label="وصف اختياري"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="غرض الاجتماع أو تعليمات سريعة"
          multiline
        />
        <TextField
          id="hostName"
          label="اسم العرض للمالك"
          value={hostName}
          onChange={(event) => setHostName(event.target.value)}
          placeholder="أحمد"
          required
        />
        <TextField
          id="maxParticipants"
          label="الحد الأقصى للمشاركين"
          type="number"
          value={maxParticipants}
          onChange={(event) => setMaxParticipants(event.target.value)}
          required
        />
        <TextField
          id="expiresInHours"
          label="مدة الدعوة الأولية بالساعات"
          type="number"
          value={expiresInHours}
          onChange={(event) => setExpiresInHours(event.target.value)}
        />
        <p className="small muted">يمكنك إنشاء دعوات إضافية أو إبطالها من صفحة إدارة الغرفة بعد الإنشاء.</p>
        <div className="form-actions">
          <ActionButton type="submit" disabled={loading}>
            {loading ? "جارٍ الإنشاء" : "إنشاء الغرفة"}
          </ActionButton>
          <ActionButton variant="secondary" onClick={() => navigate("/app")}>
            العودة
          </ActionButton>
        </div>
      </form>
      {error ? (
        <StatusBanner title="تعذر إنشاء الغرفة">{error}</StatusBanner>
      ) : null}
    </div>
  );
}

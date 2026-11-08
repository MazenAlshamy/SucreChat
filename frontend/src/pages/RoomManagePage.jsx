import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  closeRoom,
  createInvitation,
  decideJoinRequest,
  revokeInvitation,
} from "../api/client";
import ActionButton from "../components/ActionButton";
import ChatPanel from "../components/ChatPanel";
import ConnectionStatus from "../components/ConnectionStatus";
import MeetingTimer from "../components/MeetingTimer";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import TextField from "../components/TextField";
import { useRoomSession } from "../context/RoomSessionContext";
import { useSession } from "../context/SessionContext";

export default function RoomManagePage() {
  const location = useLocation();
  const session = useRoomSession();
  const { refreshSummary } = useSession();
  const [message, setMessage] = useState("");
  const [maxUses, setMaxUses] = useState("");
  const [expiresInHours, setExpiresInHours] = useState("24");
  const [freshCode, setFreshCode] = useState(location.state?.freshInviteCode || "");
  const [localError, setLocalError] = useState("");

  useEffect(() => {
    if (location.hash === "#join-requests") {
      document.getElementById("join-requests")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [location.hash, session?.detail]);

  if (!session) {
    return <div className="card">جارٍ تحميل الغرفة.</div>;
  }

  const { roomId, detail, error, connection, media, messages, chatError, chatLoading, unreadChat, elapsedSeconds, reload, postChat, markChatRead } =
    session;

  async function handleCreateInvite(event) {
    event.preventDefault();
    setLocalError("");
    try {
      const invitation = await createInvitation(roomId, {
        max_uses: maxUses ? Number(maxUses) : null,
        expires_in_hours: expiresInHours ? Number(expiresInHours) : null,
      });
      setFreshCode(invitation.code || "");
      setMessage("تم إنشاء دعوة جديدة.");
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  async function copyLink(code) {
    const url = `${window.location.origin}/join/${code}`;
    try {
      await navigator.clipboard.writeText(url);
      setMessage("تم نسخ رابط الدعوة.");
    } catch {
      setMessage(url);
    }
  }

  async function handleDecision(requestId, decision) {
    setLocalError("");
    try {
      await decideJoinRequest(requestId, decision);
      setMessage(decision === "approved" ? "تمت الموافقة." : "تم الرفض.");
      await reload();
      await refreshSummary();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  async function handleRevoke(invitationId) {
    try {
      await revokeInvitation(invitationId);
      setMessage("أُبطلت الدعوة. لن تُقبل استخدامات جديدة.");
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  async function handleClose() {
    try {
      await closeRoom(roomId);
      setMessage("أُغلقت الغرفة.");
      await reload();
    } catch (err) {
      setLocalError(err.message);
    }
  }

  if (!detail) {
    return <div className="card">{error || "جارٍ تحميل الغرفة."}</div>;
  }

  const pending = (detail.join_requests || []).filter((item) => item.status === "pending");
  const isOwner = Boolean(detail.room.is_owner || detail.role === "owner");
  const mediaLive = media.status === "connected";

  return (
    <div className="stack">
      <div className="card">
        <PageHeader
          kicker={isOwner ? "إدارة الغرفة" : "تفاصيل الغرفة"}
          title={detail.room.name}
          description={detail.room.description || "لا يوجد وصف."}
        />
        <div className="meeting-status">
          <ConnectionStatus status={connection.status} />
          <MeetingTimer seconds={elapsedSeconds} running={Boolean(detail.meeting_running)} />
          <span className={`status-chip ${detail.room.status === "active" ? "" : "danger"}`}>
            الحالة: {detail.room.status}
          </span>
          {mediaLive ? <span className="status-chip">الوسائط تعمل في الخلفية</span> : null}
        </div>
        <p className="small">
          المشاركون: {detail.room.member_count} / {detail.room.max_participants} — الطلبات المعلقة: {pending.length}
        </p>
        <div className="form-actions">
          <Link to={`/rooms/${roomId}/meeting`}>
            <ActionButton>{mediaLive ? "العودة إلى الاجتماع" : "دخول واجهة الغرفة"}</ActionButton>
          </Link>
          {isOwner ? (
            <ActionButton variant="secondary" onClick={handleClose}>
              إغلاق الغرفة
            </ActionButton>
          ) : null}
          <Link to="/rooms">
            <ActionButton variant="ghost">العودة إلى الغرف</ActionButton>
          </Link>
          <Link to="/app">
            <ActionButton variant="ghost">لوحة التحكم</ActionButton>
          </Link>
        </div>
      </div>

      {isOwner ? (
        <div className="card" id="join-requests">
          <h2>طلبات الانضمام {pending.length ? `(${pending.length})` : ""}</h2>
          <div className="form-actions">
            <ActionButton variant="ghost" onClick={() => reload().catch((err) => setLocalError(err.message))}>
              تحديث القائمة
            </ActionButton>
          </div>
          {pending.length === 0 ? <p>لا توجد طلبات معلقة.</p> : null}
          {pending.map((item) => (
            <article key={item.id} className="grid-card">
              <strong>{item.display_name}</strong>
              <p className="small">قُدّم في {new Date(item.created_at).toLocaleString("ar")}</p>
              <div className="form-actions">
                <ActionButton onClick={() => handleDecision(item.id, "approved")}>قبول</ActionButton>
                <ActionButton variant="secondary" onClick={() => handleDecision(item.id, "rejected")}>
                  رفض
                </ActionButton>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {isOwner ? (
        <div className="card">
          <h2>الدعوات</h2>
          {freshCode ? (
            <StatusBanner title="رابط الدعوة الحالي" tone="warning">
              {`${window.location.origin}/join/${freshCode}`}
              <div className="form-actions">
                <ActionButton variant="secondary" onClick={() => copyLink(freshCode)}>
                  نسخ الرابط
                </ActionButton>
              </div>
            </StatusBanner>
          ) : (
            <p className="small">يظهر الرمز الكامل مرة واحدة عند الإنشاء فقط.</p>
          )}
          <form onSubmit={handleCreateInvite}>
            <div className="page-grid">
              <TextField
                id="maxUses"
                label="حد الاستخدامات"
                type="number"
                value={maxUses}
                onChange={(event) => setMaxUses(event.target.value)}
                placeholder="بدون حد"
              />
              <TextField
                id="expires"
                label="تنتهي بعد ساعات"
                type="number"
                value={expiresInHours}
                onChange={(event) => setExpiresInHours(event.target.value)}
              />
            </div>
            <ActionButton type="submit">إنشاء دعوة جديدة</ActionButton>
          </form>
          <div className="stack" style={{ marginTop: 16 }}>
            {(detail.invitations || []).map((invitation) => (
              <article key={invitation.id} className="grid-card">
                <strong>بادئة الرمز: {invitation.code_prefix}</strong>
                <p className="small">
                  الحالة: {invitation.status} — الاستخدامات: {invitation.use_count}
                  {invitation.max_uses ? ` / ${invitation.max_uses}` : " / بدون حد"}
                </p>
                {invitation.status === "active" ? (
                  <ActionButton variant="secondary" onClick={() => handleRevoke(invitation.id)}>
                    إبطال الدعوة
                  </ActionButton>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}

      <div className="card">
        <h2>الأعضاء المعتمدون</h2>
        {(detail.members || []).map((member) => (
          <p key={member.id || member.user_id} className="small">
            {member.display_name} — {member.role}
            {member.online ? " — متصل" : ""}
          </p>
        ))}
      </div>

      <ChatPanel
        title={detail.room.name}
        messages={messages}
        currentUserId={detail.user_id}
        onSend={postChat}
        error={chatError}
        onRead={markChatRead}
        loading={chatLoading}
        unreadCount={unreadChat}
      />

      {message ? <StatusBanner title="تم" tone="success">{message}</StatusBanner> : null}
      {localError || error ? <StatusBanner title="تعذر تنفيذ العملية">{localError || error}</StatusBanner> : null}
    </div>
  );
}

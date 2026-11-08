import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import ActionButton from "../components/ActionButton";
import ChatPanel from "../components/ChatPanel";
import ConnectionStatus from "../components/ConnectionStatus";
import MeetingTimer from "../components/MeetingTimer";
import PageHeader from "../components/PageHeader";
import ParticipantTile from "../components/ParticipantTile";
import StatusBanner from "../components/StatusBanner";
import { useRoomSession } from "../context/RoomSessionContext";
import { meetingGridClass } from "../meetingLayout";

function mediaLabel(status) {
  if (status === "connected") {
    return "الوسائط متصلة";
  }
  if (status === "connecting") {
    return "جارٍ الاتصال بالوسائط";
  }
  if (status === "error") {
    return "تعذر اتصال الوسائط";
  }
  return "الوسائط غير متصلة";
}

export default function MeetingPage() {
  const navigate = useNavigate();
  const session = useRoomSession();
  const [showPeople, setShowPeople] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const {
    detail,
    error,
    connection,
    media,
    provider,
    messages,
    chatError,
    chatLoading,
    elapsedSeconds,
    postChat,
    markChatRead,
    setChatOpen,
    unreadChat,
    leaveMedia,
  } = session || {};

  useEffect(() => {
    if (!setChatOpen) {
      return undefined;
    }
    setChatOpen(showChat);
    if (showChat) {
      markChatRead?.();
    }
    return undefined;
  }, [showChat, setChatOpen, markChatRead]);

  useEffect(() => {
    function unlockAudio() {
      document.querySelectorAll("audio").forEach((element) => {
        element.muted = false;
        const play = element.play?.();
        play?.catch?.(() => {});
      });
    }
    window.addEventListener("pointerdown", unlockAudio, { once: true });
    return () => window.removeEventListener("pointerdown", unlockAudio);
  }, []);

  if (!session) {
    return <div className="card">جارٍ تجهيز الغرفة.</div>;
  }

  async function handleLeave() {
    await leaveMedia();
    navigate("/app");
  }

  if (error) {
    return (
      <div className="card">
        <PageHeader title="لا يمكن دخول الغرفة" description={error} />
        <Link to="/app">
          <ActionButton>العودة</ActionButton>
        </Link>
      </div>
    );
  }

  if (!detail) {
    return <div className="card">جارٍ التحقق من صلاحية العضوية.</div>;
  }

  const tiles = media.participants || [];
  const peopleCount = tiles.filter((item) => !item.screenOn).length;
  const connectedCount = tiles.length;
  const mediaConnected = media.status === "connected";
  const pending = (detail.join_requests || []).filter((item) => item.status === "pending").length;

  return (
    <div className={`meeting-shell ${showChat ? "with-chat" : ""}`}>
      <div className="meeting-main">
        <div className="meeting-top">
          <PageHeader kicker="اجتماع خاص" title={detail.room.name} />
          <div className="meeting-status">
            <ConnectionStatus status={connection.status} />
            <MeetingTimer seconds={elapsedSeconds} running={Boolean(detail.meeting_running)} />
            <span
              className={`status-chip ${mediaConnected && !media.error ? "" : media.status === "connecting" || mediaConnected ? "warn" : "danger"}`}
            >
              {media.error && mediaConnected ? "متصل بدون كاميرا/ميكروفون" : mediaLabel(media.status)}
            </span>
          </div>
        </div>

        {detail.media_enabled ? (
          provider === "webrtc" ? (
            <StatusBanner title="اتصال الند للند">
              المسار الحالي WebRTC بين الأعضاء المعتمدين. مكالمة بين جهازين تحتاج أذونات الكاميرا/الميكروفون في المتصفح، وHTTPS خارج localhost. LiveKit اختياري عبر backend/.env.
            </StatusBanner>
          ) : null
        ) : (
          <StatusBanner title="خادم الوسائط غير مُعد">
            ضع LIVEKIT_URL وLIVEKIT_API_KEY وLIVEKIT_API_SECRET في backend/.env ثم أعد تشغيل الخادم، أو اترك WEBRTC_FALLBACK=true لاستخدام اتصال الند للند.
          </StatusBanner>
        )}
        {media.error ? <StatusBanner title="تعذر تشغيل الوسائط">{media.error}</StatusBanner> : null}
        {tiles.some((item) => item.videoLost) ? (
          <StatusBanner title="انقطع عرض الفيديو">
            ظهر الفيديو ثم توقف عند أحد المشاركين. الصوت قد يبقى يعمل. استخدم إعادة الاتصال إن استمر الانقطاع.
          </StatusBanner>
        ) : null}

        <div className={`video-grid ${meetingGridClass(connectedCount)}`}>
          {tiles.length ? (
            tiles.map((participant) => (
              <ParticipantTile key={participant.identity} participant={participant} />
            ))
          ) : (
            <div className="empty-stage">
              {mediaConnected
                ? "أنت في الاجتماع. سيظهر المشاركون الآخرون هنا عند اتصالهم."
                : detail.media_enabled
                  ? "بانتظار اتصال الوسائط."
                  : "لا يمكن عرض الفيديو قبل إعداد مسار الوسائط."}
            </div>
          )}
        </div>

        <div className="control-bar">
          <ActionButton
            variant={media.micOn ? "primary" : "secondary"}
            disabled={!mediaConnected}
            onClick={media.toggleMic}
          >
            {media.micOn ? "كتم الميكروفون" : "تشغيل الميكروفون"}
          </ActionButton>
          <ActionButton
            variant={media.camOn ? "primary" : "secondary"}
            disabled={!mediaConnected}
            onClick={media.toggleCam}
          >
            {media.camOn ? "إيقاف الكاميرا" : "تشغيل الكاميرا"}
          </ActionButton>
          <ActionButton
            variant={media.screenOn ? "primary" : "secondary"}
            disabled={!mediaConnected}
            onClick={media.toggleScreen}
          >
            {media.screenOn ? "إيقاف مشاركة الشاشة" : "مشاركة الشاشة"}
          </ActionButton>
          <ActionButton variant="ghost" onClick={() => setShowPeople((value) => !value)}>
            المشاركون ({peopleCount})
          </ActionButton>
          <ActionButton variant="ghost" onClick={() => setShowChat((value) => !value)}>
            {showChat ? "إخفاء المحادثة" : unreadChat ? `المحادثة (${unreadChat})` : "المحادثة"}
          </ActionButton>
          {media.status === "error" || media.status === "disconnected" || media.error ? (
            <ActionButton variant="secondary" disabled={!detail.media_enabled} onClick={media.reconnect}>
              إعادة الاتصال
            </ActionButton>
          ) : null}
          <ActionButton variant="ghost" onClick={handleLeave}>
            مغادرة الاجتماع
          </ActionButton>
          {detail.role === "owner" ? (
            <Link to={`/rooms/${detail.room.id}#join-requests`}>
              <ActionButton variant="ghost">
                إدارة الغرفة{pending ? ` (${pending})` : ""}
              </ActionButton>
            </Link>
          ) : (
            <Link to={`/rooms/${detail.room.id}`}>
              <ActionButton variant="ghost">تفاصيل الغرفة</ActionButton>
            </Link>
          )}
          <Link to="/rooms">
            <ActionButton variant="ghost">العودة إلى الغرف</ActionButton>
          </Link>
        </div>

        {mediaConnected ? (
          <div className="device-row">
            {media.devices.mics.length > 1 ? (
              <label>
                الميكروفون
                <select
                  value={media.selected.micId}
                  onChange={(event) => media.switchDevice("audioinput", event.target.value)}
                >
                  <option value="">الافتراضي</option>
                  {media.devices.mics.map((device) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || "ميكروفون"}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {media.devices.cameras.length > 1 ? (
              <label>
                الكاميرا
                <select
                  value={media.selected.cameraId}
                  onChange={(event) => media.switchDevice("videoinput", event.target.value)}
                >
                  <option value="">الافتراضي</option>
                  {media.devices.cameras.map((device) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || "كاميرا"}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            {media.devices.speakers.length > 1 ? (
              <label>
                السماعة
                <select
                  value={media.selected.speakerId}
                  onChange={(event) => media.switchDevice("audiooutput", event.target.value)}
                >
                  <option value="">الافتراضي</option>
                  {media.devices.speakers.map((device) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || "سماعة"}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
        ) : null}

        {showPeople ? (
          <div className="card people-list">
            <h2>المشاركون المتصلون</h2>
            {tiles.filter((item) => !item.screenOn).length ? (
              tiles
                .filter((item) => !item.screenOn)
                .map((person) => (
                  <p key={person.identity} className="small">
                    {person.name}
                    {person.isLocal ? " (أنت)" : ""} — {person.micOn ? "ميكروفون يعمل" : "صامت"} —{" "}
                    {person.cameraOn ? "كاميرا تعمل" : "بدون فيديو"}
                  </p>
                ))
            ) : (
              <p className="small">لا يوجد مشاركون في مسار الوسائط حالياً. العدد يعكس من اتصل بالوسائط وليس مجرد فتح الصفحة.</p>
            )}
          </div>
        ) : null}
      </div>
      {showChat ? (
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
      ) : null}
    </div>
  );
}

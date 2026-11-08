import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useRoomSession } from "../context/RoomSessionContext";
import { useSession } from "../context/SessionContext";
import ActionButton from "./ActionButton";
import MeetingTimer from "./MeetingTimer";

export default function AppLayout() {
  const { user, summary, logout, toast } = useSession();
  const roomSession = useRoomSession();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const liveMeeting =
    roomSession?.mediaHeld &&
    roomSession?.detail?.room &&
    !roomSession?.inMeeting &&
    roomSession?.media?.status === "connected";
  const pending = summary.join_requests || 0;
  const unread = summary.notifications || 0;
  const unreadMessages = summary.messages || 0;
  const links = user
    ? [
        { to: "/app", label: "لوحة التحكم", end: true },
        { to: "/rooms", label: "غرفي" },
        { to: "/create", label: "إنشاء غرفة" },
        { to: "/notifications", label: unread ? `الإشعارات (${unread})` : "الإشعارات" },
      ]
    : [
        { to: "/", label: "الرئيسية", end: true },
        { to: "/login", label: "تسجيل الدخول" },
        { to: "/register", label: "إنشاء حساب" },
      ];

  useEffect(() => {
    setMenuOpen(false);
  }, [user, unread, pending, location.pathname]);

  async function handleLogout() {
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="container header-inner">
          <NavLink to={user ? "/app" : "/"} className="brand">
            <span className="brand-mark">S</span>
            <span>SecureChat</span>
          </NavLink>
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={menuOpen}
            aria-label="القائمة"
            onClick={() => setMenuOpen((value) => !value)}
          >
            القائمة
          </button>
          <nav className={`nav-links ${menuOpen ? "open" : ""}`}>
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) => (isActive ? "active" : undefined)}
                end={link.end}
                onClick={() => setMenuOpen(false)}
              >
                {link.label}
              </NavLink>
            ))}
            {user ? (
              <>
                {pending ? (
                  <Link
                    to={
                      roomSession?.detail?.room &&
                      (roomSession.detail.room.is_owner || roomSession.detail.role === "owner")
                        ? `/rooms/${roomSession.detail.room.id}#join-requests`
                        : "/rooms"
                    }
                    className="status-chip warn"
                    onClick={() => setMenuOpen(false)}
                  >
                    طلبات: {pending}
                  </Link>
                ) : null}
                {unreadMessages ? (
                  <span className="status-chip warn">رسائل: {unreadMessages}</span>
                ) : null}
                <span className="nav-user">{user.display_name}</span>
                <ActionButton variant="ghost" onClick={handleLogout}>
                  خروج
                </ActionButton>
              </>
            ) : null}
          </nav>
        </div>
      </header>
      {toast ? <div className="toast-banner">{toast}</div> : null}
      {liveMeeting ? (
        <div className="toast-banner meeting-dock">
          <span>
            الاجتماع مستمر في {roomSession.detail.room.name} — الوسائط لم تُقطع
          </span>
          <MeetingTimer
            seconds={roomSession.elapsedSeconds}
            running={Boolean(roomSession.detail.meeting_running)}
          />
          <Link to={`/rooms/${roomSession.detail.room.id}/meeting`}>
            <ActionButton>العودة إلى الاجتماع</ActionButton>
          </Link>
        </div>
      ) : null}
      <main className="main">
        <div className="container">
          <Outlet />
        </div>
      </main>
      <footer className="site-footer">
        <div className="container footer-inner">
          <span>SecureChat — غرف خاصة باجتماعات صوت وصورة</span>
          <span className="muted small">الوسائط للأعضاء المعتمدين فقط</span>
        </div>
      </footer>
    </div>
  );
}

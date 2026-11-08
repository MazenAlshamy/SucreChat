import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "../context/SessionContext";

export default function RequireSession() {
  const { user, ready } = useSession();
  const location = useLocation();

  if (!ready) {
    return (
      <div className="card auth-card">
        <p className="small">جارٍ التحقق من الجلسة.</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

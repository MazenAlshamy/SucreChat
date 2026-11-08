import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import ActionButton from "./ActionButton";

const LANDING_LINKS = [
  { href: "/#top", label: "الرئيسية" },
  { href: "/#features", label: "المميزات" },
  { href: "/#how", label: "كيف تعمل المنصة؟" },
  { href: "/#security", label: "الأمان والخصوصية" },
];

export default function PublicLayout() {
  const { user, logout } = useSession();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname, location.hash, user]);

  return (
    <div className="app-shell public-shell">
      <header className="site-header landing-header">
        <div className="container header-inner">
          <NavLink to="/" className="brand">
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
            {LANDING_LINKS.map((link) => (
              <a key={link.href} href={link.href} onClick={() => setMenuOpen(false)}>
                {link.label}
              </a>
            ))}
            {user ? (
              <>
                <NavLink to="/app" onClick={() => setMenuOpen(false)}>
                  لوحة التحكم
                </NavLink>
                <span className="nav-user">{user.display_name}</span>
                <ActionButton variant="ghost" onClick={logout}>
                  خروج
                </ActionButton>
              </>
            ) : (
              <>
                <NavLink to="/login" onClick={() => setMenuOpen(false)}>
                  تسجيل الدخول
                </NavLink>
                <NavLink to="/register" className="nav-cta" onClick={() => setMenuOpen(false)}>
                  إنشاء حساب
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className={`main public-main${location.pathname === "/" ? "" : " public-auth"}`}>
        {location.pathname === "/" ? (
          <Outlet />
        ) : (
          <div className="container">
            <Outlet />
          </div>
        )}
      </main>
      <footer className="site-footer landing-footer">
        <div className="container footer-grid">
          <div>
            <NavLink to="/" className="brand">
              <span className="brand-mark">S</span>
              <span>SecureChat</span>
            </NavLink>
            <p className="small">منصة للغرف الخاصة والاجتماعات الصوتية والمرئية للأعضاء المعتمدين.</p>
          </div>
          <div>
            <h3>التنقل</h3>
            <a href="/#features">المميزات</a>
            <a href="/#how">كيف تعمل المنصة؟</a>
            <a href="/#security">الأمان والخصوصية</a>
            <Link to="/join">الانضمام عبر دعوة</Link>
          </div>
          <div>
            <h3>الحساب</h3>
            <Link to="/login">تسجيل الدخول</Link>
            <Link to="/register">إنشاء حساب</Link>
            <Link to="/verify-email">تأكيد البريد</Link>
            {user ? <Link to="/app">لوحة التحكم</Link> : null}
          </div>
          <div>
            <h3>المنصة</h3>
            <p className="small">الغرف خاصة وبدعوة. الدخول بعد موافقة المالك عند الحاجة.</p>
            <p className="small muted">سياسة الخصوصية وشروط الاستخدام تُعرض عند إنشاء الحساب.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

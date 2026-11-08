export default function StatusBanner({ tone = "warning", title, children }) {
  return (
    <div className={`notice ${tone}`}>
      <strong>{title}</strong>
      <div className="small" style={{ marginBottom: 0 }}>
        {children}
      </div>
    </div>
  );
}

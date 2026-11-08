const LABELS = {
  connected: "متصل مباشرة",
  connecting: "جارٍ الاتصال",
  disconnected: "انقطع الاتصال — إعادة المحاولة",
};

export default function ConnectionStatus({ status }) {
  const tone = status === "connected" ? "" : status === "connecting" ? "warn" : "danger";
  return <span className={`status-chip ${tone}`}>{LABELS[status] || status}</span>;
}

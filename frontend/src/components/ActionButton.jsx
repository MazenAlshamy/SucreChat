export default function ActionButton({
  children,
  variant = "primary",
  type = "button",
  disabled = false,
  onClick,
}) {
  const className = [
    "button",
    variant === "secondary" ? "secondary" : "",
    variant === "ghost" ? "ghost" : "",
    variant === "danger" ? "danger" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={className} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
}

const AUTH_PAGES = new Set(["/login", "/register", "/verify-email"]);

export function safeReturnPath(value, fallback = "/app") {
  if (typeof value !== "string" || !value) {
    return fallback;
  }
  const path = value.split("?")[0].split("#")[0];
  if (!path.startsWith("/") || path.startsWith("//") || path.startsWith("/\\")) {
    return fallback;
  }
  if (path.includes("://") || path.includes("\\")) {
    return fallback;
  }
  if (path === "/" || AUTH_PAGES.has(path)) {
    return fallback;
  }
  return path;
}

export function prefersReducedMotion() {
  if (typeof window === "undefined" || !window.matchMedia) {
    return false;
  }
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

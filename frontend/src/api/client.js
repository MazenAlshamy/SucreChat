const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function getCookie(name) {
  const parts = document.cookie.split(";").map((item) => item.trim());
  const match = parts.find((item) => item.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : "";
}

function extractMessage(errorBody, fallback) {
  if (!errorBody) {
    return fallback;
  }
  if (typeof errorBody.detail === "string") {
    return errorBody.detail;
  }
  if (errorBody.detail?.message) {
    return errorBody.detail.message;
  }
  if (Array.isArray(errorBody.detail) && errorBody.detail[0]?.msg) {
    return "البيانات المرسلة غير صالحة";
  }
  return fallback;
}

async function request(path, options = {}) {
  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...options.headers,
  };
  const csrf = getCookie("sc_csrf");
  if (csrf && !headers["X-CSRF-Token"]) {
    headers["X-CSRF-Token"] = csrf;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(extractMessage(data, "تعذر إكمال الطلب"));
    error.status = response.status;
    error.payload = data?.detail || data;
    throw error;
  }
  return data;
}

export function fetchHealth() {
  return request("/health");
}

export function fetchSession() {
  return request("/session");
}

export function bootstrapSession(displayName) {
  return request("/session", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName }),
  });
}

export function createRoom(payload) {
  return request("/rooms", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listRooms() {
  return request("/rooms");
}

export function getRoom(roomId) {
  return request(`/rooms/${roomId}`);
}

export function closeRoom(roomId) {
  return request(`/rooms/${roomId}/close`, { method: "POST" });
}

export function createInvitation(roomId, payload) {
  return request(`/rooms/${roomId}/invitations`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function revokeInvitation(invitationId) {
  return request(`/invitations/${invitationId}/revoke`, { method: "POST" });
}

export function previewInvite(code) {
  return request(`/invites/${encodeURIComponent(code)}`);
}

export function submitJoinRequest(payload) {
  return request("/join-requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getJoinRequest(requestId) {
  return request(`/join-requests/${requestId}`);
}

export function decideJoinRequest(requestId, decision) {
  return request(`/join-requests/${requestId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });
}

export function getMeeting(roomId) {
  return request(`/rooms/${roomId}/meeting`);
}

export function getLiveKitToken(roomId) {
  return request(`/rooms/${roomId}/livekit-token`, { method: "POST" });
}

export function logout() {
  return request("/session", { method: "DELETE" });
}

export function fetchCaptcha() {
  return request("/accounts/captcha");
}

export function registerAccount(payload) {
  return request("/accounts/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginAccount(payload) {
  return request("/accounts/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyEmail(payload) {
  return request("/accounts/verify-email", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resendVerification(payload) {
  return request("/accounts/resend-verification", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMessages(roomId) {
  return request(`/rooms/${roomId}/messages`);
}

export function sendMessage(roomId, body) {
  return request(`/rooms/${roomId}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export function markMessagesRead(roomId) {
  return request(`/rooms/${roomId}/messages/read`, { method: "POST" });
}

export function listNotifications() {
  return request("/notifications");
}

export function markNotificationRead(notificationId) {
  return request(`/notifications/${notificationId}/read`, { method: "POST" });
}

export function markAllNotificationsRead() {
  return request("/notifications/read-all", { method: "POST" });
}

export function fetchInboxSummary() {
  return request("/inbox/summary");
}

export function mergeChatMessages(current, incoming) {
  const list = Array.isArray(current) ? current.slice() : [];
  const extras = Array.isArray(incoming) ? incoming : incoming ? [incoming] : [];
  const seen = new Set(list.map((item) => item?.id).filter(Boolean));
  for (const item of extras) {
    if (!item?.id || seen.has(item.id)) {
      continue;
    }
    seen.add(item.id);
    list.push(item);
  }
  return list.sort((left, right) => {
    const a = Date.parse(left.created_at || "") || 0;
    const b = Date.parse(right.created_at || "") || 0;
    if (a !== b) {
      return a - b;
    }
    return String(left.id).localeCompare(String(right.id));
  });
}

export function canSendChat(body, maxLength = 1000) {
  const cleaned = String(body || "").trim();
  if (!cleaned) {
    return { ok: false, reason: "empty" };
  }
  if (cleaned.length > maxLength) {
    return { ok: false, reason: "too_long" };
  }
  return { ok: true, body: cleaned };
}

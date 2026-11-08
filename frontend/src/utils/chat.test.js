import { strict as assert } from "node:assert";
import { test } from "node:test";
import { canSendChat, mergeChatMessages } from "./chat.js";

test("empty and oversized chat bodies are rejected", () => {
  assert.equal(canSendChat("").ok, false);
  assert.equal(canSendChat("   ").ok, false);
  assert.equal(canSendChat("x".repeat(1001)).ok, false);
  assert.equal(canSendChat("مرحبا").ok, true);
  assert.equal(canSendChat("مرحبا").body, "مرحبا");
});

test("chat history merges without duplicates and keeps chronological order", () => {
  const first = { id: "2", body: "ثانية", created_at: "2026-01-01T00:00:02Z" };
  const second = { id: "1", body: "أولى", created_at: "2026-01-01T00:00:01Z" };
  const merged = mergeChatMessages([first], [second, first]);
  assert.deepEqual(
    merged.map((item) => item.id),
    ["1", "2"]
  );
});

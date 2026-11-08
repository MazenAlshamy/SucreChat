import assert from "node:assert/strict";
import test from "node:test";
import { safeReturnPath } from "./navigation.js";

test("keeps internal app paths", () => {
  assert.equal(safeReturnPath("/app"), "/app");
  assert.equal(safeReturnPath("/rooms/abc/meeting"), "/rooms/abc/meeting");
  assert.equal(safeReturnPath("/notifications"), "/notifications");
});

test("rejects external or unsafe return paths", () => {
  assert.equal(safeReturnPath("https://evil.example/phish"), "/app");
  assert.equal(safeReturnPath("//evil.example"), "/app");
  assert.equal(safeReturnPath("/\\evil"), "/app");
  assert.equal(safeReturnPath(""), "/app");
  assert.equal(safeReturnPath(null), "/app");
});

test("auth pages and landing do not loop after login", () => {
  assert.equal(safeReturnPath("/login"), "/app");
  assert.equal(safeReturnPath("/register"), "/app");
  assert.equal(safeReturnPath("/verify-email"), "/app");
  assert.equal(safeReturnPath("/"), "/app");
});

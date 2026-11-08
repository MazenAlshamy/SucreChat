import { strict as assert } from "node:assert";
import { test } from "node:test";
import { meetingGridClass } from "./meetingLayout.js";
import { formatElapsed } from "./utils/time.js";

test("single participant fills one cell", () => {
  assert.equal(meetingGridClass(0), "count-1");
  assert.equal(meetingGridClass(1), "count-1");
});

test("two participants split evenly", () => {
  assert.equal(meetingGridClass(2), "count-2");
});

test("three and four participants use balanced grids", () => {
  assert.equal(meetingGridClass(3), "count-3");
  assert.equal(meetingGridClass(4), "count-4");
});

test("larger rooms grow columns automatically", () => {
  assert.equal(meetingGridClass(5), "count-6");
  assert.equal(meetingGridClass(6), "count-6");
  assert.equal(meetingGridClass(8), "count-9");
  assert.equal(meetingGridClass(12), "count-many");
});

test("screen tiles do not change the people grid classes", () => {
  assert.equal(meetingGridClass(4), "count-4");
  assert.equal(meetingGridClass(5), "count-6");
});

test("elapsed timer always includes hours", () => {
  assert.equal(formatElapsed(0), "00:00:00");
  assert.equal(formatElapsed(35 * 60 + 42), "00:35:42");
  assert.equal(formatElapsed(3600 + 5), "01:00:05");
});

export function meetingGridClass(count) {
  const size = Math.max(0, Number(count) || 0);
  if (size <= 1) {
    return "count-1";
  }
  if (size === 2) {
    return "count-2";
  }
  if (size === 3) {
    return "count-3";
  }
  if (size === 4) {
    return "count-4";
  }
  if (size <= 6) {
    return "count-6";
  }
  if (size <= 9) {
    return "count-9";
  }
  return "count-many";
}

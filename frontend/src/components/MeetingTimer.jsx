import { formatElapsed } from "../utils/time";

export default function MeetingTimer({ seconds, running }) {
  return (
    <span className={`status-chip ${running ? "" : "warn"}`} title="مدة الاجتماع من الخادم">
      {running ? "مدة الاجتماع" : "توقف المؤقت"}: {formatElapsed(seconds)}
    </span>
  );
}

import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getJoinRequest } from "../api/client";
import ActionButton from "../components/ActionButton";
import ConnectionStatus from "../components/ConnectionStatus";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import useRealtime from "../hooks/useRealtime";

const STATUS_COPY = {
  pending: "تم إرسال طلبك بنجاح. أنت الآن بانتظار موافقة مالك الغرفة.",
  approved: "تمت الموافقة على طلبك. يمكنك دخول واجهة الغرفة.",
  rejected: "رفض مالك الغرفة طلب الانضمام.",
  cancelled: "أُلغي طلب الانضمام.",
};

export default function WaitingApprovalPage() {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const [request, setRequest] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getJoinRequest(requestId)
      .then(setRequest)
      .catch((err) => setError(err.message));
  }, [requestId]);

  const status = useRealtime(
    requestId ? `/api/ws/join-requests/${requestId}` : "",
    (event) => {
      if (event.request) {
        setRequest(event.request);
      }
    },
    Boolean(requestId) && !error
  );

  useEffect(() => {
    if (request?.status === "approved") {
      navigate(`/rooms/${request.room_id}/meeting`);
    }
  }, [navigate, request]);

  return (
    <div className="card">
      <PageHeader
        kicker="طلب انضمام"
        title="انتظار موافقة المالك"
        description="تُحدَّث الحالة فوراً عبر WebSocket عند قرار المالك."
      />
      <ConnectionStatus status={status.status} />
      {request ? (
        <>
          <span className={`status-chip ${request.status === "pending" ? "warn" : request.status === "approved" ? "" : "danger"}`}>
            {request.room_name} — {request.status}
          </span>
          <p>{STATUS_COPY[request.status] || "حالة غير معروفة."}</p>
        </>
      ) : (
        <p>جارٍ تحميل حالة الطلب.</p>
      )}
      {error ? <StatusBanner title="تعذر قراءة الحالة">{error}</StatusBanner> : null}
      <div className="form-actions">
        <Link to="/app">
          <ActionButton variant="ghost">العودة للوحة التحكم</ActionButton>
        </Link>
        <Link to="/join">
          <ActionButton variant="ghost">دعوة أخرى</ActionButton>
        </Link>
      </div>
      <StatusBanner title="تنبيه">
        حالة الانتظار لا تمنح أي صلاحية لمشاهدة محتويات الاجتماع.
      </StatusBanner>
    </div>
  );
}

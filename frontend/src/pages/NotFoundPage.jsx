import { Link } from "react-router-dom";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";

export default function NotFoundPage() {
  return (
    <div className="card">
      <PageHeader title="الصفحة غير موجودة" description="الرابط الذي فتحته لا يطابق أي مسار في SecureChat." />
      <Link to="/">
        <ActionButton>العودة إلى الصفحة الرئيسية</ActionButton>
      </Link>
    </div>
  );
}

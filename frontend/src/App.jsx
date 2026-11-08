import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import PublicLayout from "./components/PublicLayout";
import RequireSession from "./components/RequireSession";
import { RoomSessionProvider } from "./context/RoomSessionContext";
import HomePage from "./pages/HomePage";
import LandingPage from "./pages/LandingPage";
import RegisterPage from "./pages/RegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import LoginPage from "./pages/LoginPage";
import CreateRoomPage from "./pages/CreateRoomPage";
import JoinRoomPage from "./pages/JoinRoomPage";
import WaitingApprovalPage from "./pages/WaitingApprovalPage";
import MeetingPage from "./pages/MeetingPage";
import RoomManagePage from "./pages/RoomManagePage";
import NotificationsPage from "./pages/NotificationsPage";
import RoomsPage from "./pages/RoomsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Route>
      <Route element={<RoomSessionProvider />}>
        <Route element={<AppLayout />}>
          <Route path="/join" element={<JoinRoomPage />} />
          <Route path="/join/:code" element={<JoinRoomPage />} />
          <Route path="/waiting/:requestId" element={<WaitingApprovalPage />} />
        </Route>
        <Route element={<RequireSession />}>
          <Route element={<AppLayout />}>
            <Route path="/app" element={<HomePage />} />
            <Route path="/create" element={<CreateRoomPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/rooms" element={<RoomsPage />} />
            <Route path="/rooms/:roomId" element={<RoomManagePage />} />
            <Route path="/rooms/:roomId/meeting" element={<MeetingPage />} />
            <Route path="/home" element={<Navigate to="/app" replace />} />
          </Route>
        </Route>
        <Route element={<AppLayout />}>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

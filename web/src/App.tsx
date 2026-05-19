import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./layouts/AppShell";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
      </Route>
    </Routes>
  );
}

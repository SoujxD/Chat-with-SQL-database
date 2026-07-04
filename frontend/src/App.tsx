import { Navigate, Route, Routes } from "react-router-dom";
import { NavBar } from "./components/NavBar";
import { QueryPage } from "./pages/QueryPage";
import { SchemaPage } from "./pages/SchemaPage";
import { HistoryPage } from "./pages/HistoryPage";
import { EvaluationPage } from "./pages/EvaluationPage";

export function App() {
  return (
    <div className="app-shell">
      <NavBar />
      <Routes>
        <Route path="/" element={<Navigate to="/query" replace />} />
        <Route path="/query" element={<QueryPage />} />
        <Route path="/schema" element={<SchemaPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="*" element={<Navigate to="/query" replace />} />
      </Routes>
    </div>
  );
}

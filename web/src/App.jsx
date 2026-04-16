import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import HomePage from "@/pages/HomePage";
import JobSearchPage from "@/pages/JobSearchPage";
import SkillsDashboardPage from "@/pages/SkillsDashboardPage";

function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<JobSearchPage />} />
            <Route path="/skills" element={<SkillsDashboardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;

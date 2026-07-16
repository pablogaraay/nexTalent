import "@/App.css";
import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { WorkspaceProvider } from "@/context/WorkspaceContext";

const HomePage = lazy(() => import("@/pages/HomePage"));
const JobSearchPage = lazy(() => import("@/pages/JobSearchPage"));
const SkillsDashboardPage = lazy(() => import("@/pages/SkillsDashboardPage"));
const CareerPlanPage = lazy(() => import("@/pages/CareerPlanPage"));
const ApplicationKitPage = lazy(() => import("@/pages/ApplicationKitPage"));
const PrivacyPage = lazy(() => import("@/pages/PrivacyPage"));
const WorkspacePage = lazy(() => import("@/pages/WorkspacePage"));

function PageLoader() {
  return <div className="min-h-[60vh] flex items-center justify-center" style={{ backgroundColor: "var(--parchment)" }}><div className="flex items-center gap-3 text-sm" style={{ color: "var(--olive-gray)" }}><div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--ring-warm)", borderTopColor: "transparent" }} /> Cargando herramienta...</div></div>;
}

function App() {
  return (
    <BrowserRouter>
      <WorkspaceProvider>
        <div className="flex flex-col min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
          <Navbar />
          <main className="flex-1">
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/search" element={<JobSearchPage />} />
                <Route path="/skills" element={<SkillsDashboardPage />} />
                <Route path="/career" element={<CareerPlanPage />} />
                <Route path="/workspace" element={<WorkspacePage />} />
                <Route path="/application" element={<ApplicationKitPage />} />
                <Route path="/privacy" element={<PrivacyPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </main>
          <Footer />
        </div>
      </WorkspaceProvider>
    </BrowserRouter>
  );
}

export default App;

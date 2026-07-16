import { useEffect, useMemo, useState } from "react";
import { Compass, FileText, Sparkles, Target, Upload, X } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { CareerRoadmap } from "@/components/career/CareerRoadmap";
import { CareerSummary } from "@/components/career/CareerSummary";
import { SKILL_TYPES } from "@/components/career/careerConfig";
import { SkillGapSection } from "@/components/career/SkillGapSection";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusMessage } from "@/components/ui/StatusMessage";
import { useWorkspace } from "@/context/WorkspaceContext";
import { careerAPI } from "@/lib/api";

const LOADING_STAGES = [
  "Analizando tu perfil profesional...",
  "Localizando ofertas del rol objetivo...",
  "Separando habilidades técnicas e interpersonales...",
  "Construyendo tu hoja de ruta...",
];

export default function CareerPlanPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { workspace, saveProfile, saveCareerPlan, setPlanActionComplete, acceptPrivacy } = useWorkspace();
  const requestedTargetRole = searchParams.get("targetRole") || "";
  const [targetRole, setTargetRole] = useState(requestedTargetRole);
  const [profileText, setProfileText] = useState(() => workspace.profile.text || "");
  const [inputMode, setInputMode] = useState(workspace.profile.text ? "profile" : "cv");
  const [cvFile, setCvFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(() => workspace.careerPlans.find(
    (plan) => requestedTargetRole && plan.target_role?.toLowerCase() === requestedTargetRole.toLowerCase(),
  ) || null);
  const [loadingStage, setLoadingStage] = useState(0);

  useEffect(() => {
    if (!loading) {
      setLoadingStage(0);
      return undefined;
    }
    const timer = window.setInterval(() => {
      setLoadingStage((current) => Math.min(current + 1, LOADING_STAGES.length - 1));
    }, 2200);
    return () => window.clearInterval(timer);
  }, [loading]);

  const groupedGaps = useMemo(() => {
    const groups = {
      hard: { critical: [], recommended: [], complementary: [] },
      soft: { critical: [], recommended: [], complementary: [] },
    };
    for (const gap of result?.gaps || []) {
      const type = gap.skill_type === "soft" ? "soft" : "hard";
      (groups[type][gap.priority] || groups[type].complementary).push(gap);
    }
    return groups;
  }, [result]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!targetRole.trim()) return setError("Indica el rol profesional al que quieres llegar.");
    if (inputMode === "profile" && !profileText.trim()) return setError("Describe tu perfil o sube un CV para analizar tus habilidades.");
    if (inputMode === "cv" && !cvFile) return setError("Selecciona un CV en PDF o DOCX.");
    if (inputMode === "cv" && !workspace.privacyAcceptedAt) return setError("Acepta el tratamiento temporal del CV antes de continuar.");

    const formData = new FormData();
    formData.append("targetRole", targetRole.trim());
    if (inputMode === "profile") formData.append("profileText", profileText.trim());
    if (inputMode === "cv" && cvFile) formData.append("cv", cvFile);

    setLoading(true);
    try {
      const { data } = await careerAPI.createPlan(formData);
      if (data?.error) throw new Error(data.error);
      const nextResult = data.result || null;
      setResult(nextResult);
      saveProfile({
        text: profileText,
        parsed: nextResult?.profile || workspace.profile.parsed,
        cvName: cvFile?.name || workspace.profile.cvName,
      });
      saveCareerPlan(nextResult);
    } catch (requestError) {
      const detail = requestError.response?.data?.error || requestError.response?.data?.detail || requestError.message;
      setError(typeof detail === "string" ? detail : "No se pudo generar el plan de carrera.");
    } finally {
      setLoading(false);
    }
    return undefined;
  };

  const strengthsByType = result?.strengths_by_type || {
    hard: (result?.strengths || []).filter((skill) => skill.skill_type !== "soft"),
    soft: (result?.strengths || []).filter((skill) => skill.skill_type === "soft"),
  };
  const savedPlan = workspace.careerPlans.find((plan) => plan.target_role?.toLowerCase() === result?.target_role?.toLowerCase());
  const planProgress = savedPlan ? (workspace.planProgress[savedPlan.id] || {}) : {};

  return (
    <div data-testid="career-plan-page" className="min-h-screen bg-[var(--parchment)]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <PageHeader
          badge="Análisis basado en demanda real"
          badgeIcon={Sparkles}
          title="Traza tu siguiente paso profesional"
          description="Compara tus habilidades con las ofertas de tu rol objetivo y obtén un plan accionable de hasta 12 semanas."
        />

        <Card as="form" elevated onSubmit={handleSubmit} className="mb-8">
          <div className="max-w-3xl space-y-5">
            <Field id="target-role" label="Rol objetivo">
              <div className="relative">
                <Target size={18} className="absolute left-3 top-3.5 text-[var(--terracotta)]" aria-hidden="true" />
                <input id="target-role" data-testid="target-role-input" value={targetRole} onChange={(event) => setTargetRole(event.target.value)} placeholder="Ej: Data Engineer, Product Manager..." className="nt-input pl-10" />
              </div>
            </Field>

            <div className="flex gap-2" role="group" aria-label="Origen del perfil">
              <Button variant={inputMode === "profile" ? "dark" : "secondary"} onClick={() => setInputMode("profile")}>Usar mi perfil</Button>
              <Button variant={inputMode === "cv" ? "dark" : "secondary"} onClick={() => setInputMode("cv")}>Subir CV</Button>
            </div>

            {inputMode === "profile" ? (
              <Field id="profile-description" label="Tu experiencia y habilidades">
                <textarea id="profile-description" data-testid="career-profile-input" value={profileText} onChange={(event) => setProfileText(event.target.value)} placeholder="Describe puestos, experiencia, herramientas y conocimientos actuales..." rows={6} className="nt-input" />
              </Field>
            ) : cvFile ? (
              <div className="career-upload">
                <FileText size={30} className="text-[var(--terracotta)]" aria-hidden="true" />
                <span className="mt-3 text-sm font-semibold">{cvFile.name}</span>
                <Button size="sm" variant="secondary" icon={X} onClick={() => setCvFile(null)} className="mt-3">Quitar archivo</Button>
              </div>
            ) : (
              <label htmlFor="career-cv" className="career-upload cursor-pointer">
                <input id="career-cv" data-testid="career-cv-input" type="file" accept=".pdf,.docx" className="sr-only" onChange={(event) => setCvFile(event.target.files?.[0] || null)} />
                <Upload size={30} className="text-[var(--terracotta)]" aria-hidden="true" />
                <span className="mt-3 text-sm font-semibold">Selecciona tu CV</span>
                <span className="mt-1 text-xs text-[var(--stone-gray)]">PDF o DOCX · máximo 10 MB</span>
              </label>
            )}

            {inputMode === "cv" ? (
              <label className="flex items-start gap-2 text-xs text-[var(--olive-gray)]">
                <input type="checkbox" checked={Boolean(workspace.privacyAcceptedAt)} onChange={(event) => event.target.checked && acceptPrivacy()} className="mt-0.5" />
                <span>Acepto el procesamiento temporal del CV. <Link to="/privacy" className="text-[var(--terracotta)] font-semibold">Más información</Link>.</span>
              </label>
            ) : null}
          </div>

          {error ? <div className="mt-5"><StatusMessage tone="error">{error}</StatusMessage></div> : null}
          <Button data-testid="generate-career-plan-btn" type="submit" loading={loading} icon={Compass} size="lg" className="mt-6">
            {loading ? LOADING_STAGES[loadingStage] : "Crear mi plan de carrera"}
          </Button>
        </Card>

        {result ? (
          <div className="space-y-6 animate-fade-in">
            <CareerSummary result={result} />
            {SKILL_TYPES.map((skillType) => (
              <SkillGapSection key={skillType.key} skillType={skillType} strengths={strengthsByType[skillType.key] || []} gaps={groupedGaps[skillType.key]} />
            ))}
            <CareerRoadmap
              plan={result.plan}
              progress={planProgress}
              savedPlan={savedPlan}
              onActionChange={(actionKey, checked) => savedPlan && setPlanActionComplete(savedPlan.id, actionKey, checked)}
              onPrint={() => window.print()}
              onSearch={() => navigate(`/search?role=${encodeURIComponent(result.target_role || "")}`)}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

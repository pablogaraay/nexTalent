import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SKILL_TYPES } from "@/components/career/careerConfig";

export function CareerSummary({ result }) {
  const readiness = result.readiness || {};
  const readinessByType = readiness.by_type || {};

  return (
    <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card tone="dark" className="md:col-span-2">
        <span className="text-xs uppercase tracking-wider text-[var(--warm-silver)]">Objetivo profesional</span>
        <h2 className="font-serif mt-2 mb-3 text-3xl">{result.target_role}</h2>
        <p className="text-sm text-[var(--warm-silver)]">
          Análisis construido con {result.market?.offers_analyzed || 0} ofertas y habilidades normalizadas mediante SFIA.
        </p>
        <p className="text-xs mt-2 text-[var(--warm-silver)]">
          Confianza de la muestra: {result.market?.confidence_label || "orientativa"}. La preparación mide cobertura de habilidades, no probabilidad de contratación.
        </p>
      </Card>

      <Card className="flex items-center gap-5">
        <div className="career-score" style={{ "--score": `${readiness.score || 0}%` }}>
          <div>{readiness.score || 0}%</div>
        </div>
        <div>
          <span className="text-xs text-[var(--stone-gray)]">Preparación estimada</span>
          <p className="font-serif text-xl capitalize">{readiness.label}</p>
          <span className="text-xs text-[var(--olive-gray)]">{readiness.covered_skills} de {readiness.target_skills} skills</span>
        </div>
      </Card>

      <Card>
        <span className="text-xs text-[var(--stone-gray)]">Preparación por categoría</span>
        <div className="mt-3 space-y-3">
          {SKILL_TYPES.map((skillType) => {
            const typedReadiness = readinessByType[skillType.key] || {};
            return (
              <div key={skillType.key}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold">{skillType.shortLabel}</span>
                  <span className="font-bold" style={{ color: skillType.color }}>{typedReadiness.score || 0}%</span>
                </div>
                <ProgressBar value={typedReadiness.score || 0} tone={skillType.key === "soft" ? "success" : "accent"} />
                <span className="text-xs text-[var(--stone-gray)]">{typedReadiness.covered_skills || 0} de {typedReadiness.target_skills || 0} skills</span>
              </div>
            );
          })}
        </div>
      </Card>
    </section>
  );
}

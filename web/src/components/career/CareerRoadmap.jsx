import { Printer, Search } from "lucide-react";

import { SKILL_TYPES } from "@/components/career/careerConfig";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function CareerRoadmap({ onActionChange, onPrint, onSearch, plan, progress, savedPlan }) {
  return (
    <Card className="p-6 md:p-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-7">
        <div>
          <span className="text-xs uppercase tracking-wider text-[var(--terracotta)] font-bold">{plan?.weekly_commitment} por semana</span>
          <h2 className="font-serif text-3xl mt-1">Tu hoja de ruta</h2>
        </div>
        <span className="text-sm text-[var(--olive-gray)]">Duración: {plan?.duration_weeks} semanas</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {(plan?.tracks || []).map((track) => {
          const skillType = SKILL_TYPES.find((item) => item.key === track.skill_type) || SKILL_TYPES[0];
          const Icon = skillType.icon;
          return (
            <article key={track.skill_type} className="career-track" style={{ borderTopColor: skillType.color }}>
              <div className="flex items-center gap-2 mb-2"><Icon size={18} style={{ color: skillType.color }} /><h3 className="font-serif text-xl">{track.title}</h3></div>
              <p className="text-xs mb-5 text-[var(--olive-gray)]">{track.objective}</p>
              <div className="space-y-5">
                {track.phases.map((phase) => (
                  <section key={`${track.skill_type}-${phase.phase}-${phase.title}`}>
                    <div className="flex flex-wrap items-baseline gap-x-3 mb-2">
                      <span className="career-track__number" style={{ backgroundColor: skillType.color }}>{phase.phase}</span>
                      <h4 className="text-sm font-semibold">{phase.title}</h4>
                      <span className="text-xs" style={{ color: skillType.color }}>{phase.weeks}</span>
                    </div>
                    {phase.skills?.length ? <p className="text-xs mb-3 text-[var(--olive-gray)]">Foco: {phase.skills.join(", ")}</p> : null}
                    <ul className="space-y-2">
                      {phase.actions.map((action, actionIndex) => {
                        const actionKey = `${track.skill_type}-${phase.phase}-${actionIndex}`;
                        const checked = Boolean(progress[actionKey]);
                        return (
                          <li key={action} className="flex gap-2 text-sm text-[var(--charcoal-warm)]">
                            <input type="checkbox" checked={checked} disabled={!savedPlan} onChange={(event) => onActionChange(actionKey, event.target.checked)} aria-label={`Marcar acción: ${action}`} className="mt-1" />
                            <span className={checked ? "line-through opacity-60" : ""}>{action}</span>
                          </li>
                        );
                      })}
                    </ul>
                    <div className="mt-3 p-3 rounded-lg text-xs bg-[var(--ivory)] text-[var(--olive-gray)]"><strong className="text-[var(--near-black)]">Evidencia:</strong> {phase.success_evidence}</div>
                  </section>
                ))}
              </div>
            </article>
          );
        })}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-7 pt-5 border-t border-[var(--border-cream)]">
        <Button variant="secondary" icon={Printer} onClick={onPrint}>Exportar o imprimir</Button>
        <Button icon={Search} onClick={onSearch}>Ver oportunidades relacionadas</Button>
      </div>
    </Card>
  );
}

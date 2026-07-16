import { Check, Flag } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/components/career/careerConfig";

export function SkillGapSection({ gaps, skillType, strengths }) {
  const Icon = skillType.icon;
  const hasGaps = Object.values(gaps).some((skills) => skills.length);

  return (
    <Card>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ color: skillType.color, backgroundColor: `${skillType.color}14` }}>
          <Icon size={20} aria-hidden="true" />
        </div>
        <div>
          <h2 className="font-serif text-2xl">{skillType.label}</h2>
          <p className="text-xs text-[var(--stone-gray)]">{skillType.subtitle}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm mb-3 font-semibold">Fortalezas detectadas</h3>
          {strengths.length ? (
            <div className="space-y-2">
              {strengths.map((skill) => (
                <div key={skill.skill_id} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-[rgba(92,112,82,0.08)]">
                  <div className="flex items-center gap-2 min-w-0"><Check size={16} className="text-[var(--success)]" /><span className="text-sm truncate font-semibold">{skill.skill_name}</span></div>
                  <span className="text-xs whitespace-nowrap text-[var(--olive-gray)]">{skill.share_pct}%</span>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-[var(--olive-gray)]">No se han detectado fortalezas de esta categoría.</p>}
        </div>

        <div>
          <h3 className="text-sm mb-3 font-semibold">Brecha de habilidades</h3>
          <div className="space-y-4">
            {Object.entries(gaps).map(([priority, skills]) => skills.length ? (
              <div key={priority}>
                <div className="flex items-center gap-2 mb-2 text-xs uppercase tracking-wide font-bold" style={{ color: PRIORITY_COLORS[priority] }}>
                  <Flag size={13} /> {PRIORITY_LABELS[priority]}
                </div>
                <div className="flex flex-wrap gap-2">
                  {skills.map((skill) => (
                    <span key={skill.skill_id} title={skill.reason} className="px-3 py-2 rounded-lg text-sm bg-[var(--parchment)]" style={{ borderLeft: `3px solid ${PRIORITY_COLORS[priority]}` }}>
                      {skill.skill_name} · {skill.share_pct}%
                    </span>
                  ))}
                </div>
              </div>
            ) : null)}
            {!hasGaps ? <p className="text-sm text-[var(--olive-gray)]">No se han detectado brechas de esta categoría.</p> : null}
          </div>
        </div>
      </div>
    </Card>
  );
}

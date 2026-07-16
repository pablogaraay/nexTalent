import { BadgeCheck, Briefcase, MapPin, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

export function ProfileSummary({ normalizedRoles, profile, roleExperiences }) {
  if (!roleExperiences.length && !normalizedRoles.length && !profile.role) return null;

  return (
    <Card data-testid="profile-summary" elevated className="mb-7 profile-summary">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <span className="profile-summary__icon"><Sparkles size={18} aria-hidden="true" /></span>
          <div>
            <span className="text-xs uppercase tracking-wide text-[var(--stone-gray)] font-bold">Lectura del CV</span>
            <h2 className="font-serif text-2xl">Perfil detectado</h2>
          </div>
        </div>
        {profile.skills?.length ? <Badge tone="neutral">{profile.skills.length} habilidades</Badge> : null}
      </div>

      {profile.location_query ? (
        <div className="profile-summary__fact">
          <MapPin size={15} aria-hidden="true" />
          <div><span>Ubicación preferente</span><strong>{profile.location_query}</strong></div>
        </div>
      ) : null}

      {roleExperiences.length ? (
        <div className="profile-summary__roles">
          <div className="flex items-center gap-2 mb-3"><Briefcase size={15} aria-hidden="true" /><span className="text-xs uppercase tracking-wide font-bold">Análisis de roles</span></div>
          <div className="grid gap-2">
            {roleExperiences.map((experience) => (
              <article key={`${experience.role}-${experience.normalized}-${experience.location}`} className="profile-role">
                <div><span>Rol</span><strong>{experience.role}</strong></div>
                <div><span>Equivalencia</span>{experience.normalized ? <Badge icon={BadgeCheck}>{experience.normalized}</Badge> : <em>Sin equivalencia directa</em>}</div>
                <div><span>Experiencia</span><strong>{experience.seniority || "No detectada"}</strong></div>
                <div><span>Ubicación</span><strong>{experience.location || "No detectada"}</strong></div>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {normalizedRoles.length ? (
        <div className="mt-4">
          <span className="text-xs uppercase tracking-wide text-[var(--stone-gray)] font-bold">Roles normalizados</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {normalizedRoles.map((group) => <Badge key={group.occupation} icon={BadgeCheck}>{group.occupation}{group.source_roles.length > 1 ? ` · ${group.source_roles.length} roles` : ""}</Badge>)}
          </div>
        </div>
      ) : null}

      {profile.skills?.length ? (
        <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-[var(--border-cream)]">
          {profile.skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}
        </div>
      ) : null}
    </Card>
  );
}

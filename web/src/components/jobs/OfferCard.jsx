import {
  Bookmark,
  BookmarkCheck,
  Briefcase,
  Building2,
  Compass,
  ExternalLink,
  MapPin,
  Send,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/ProgressBar";

export function OfferCard({
  animationDelay = 0,
  feedback,
  isSaved,
  isSelected,
  offer,
  onApplication,
  onCareerPlan,
  onFeedback,
  onSave,
  onSelect,
}) {
  const matchPercentage = Math.round((offer.match_score || 0) * 100);

  return (
    <Card
      as="article"
      data-testid={`offer-card-${offer.id}`}
      className={`offer-card opacity-0 animate-fade-in-up ${isSelected ? "offer-card--selected" : ""}`}
      style={{ animationDelay: `${animationDelay}s`, animationFillMode: "forwards" }}
    >
      <div className="offer-card__layout">
        <div className="offer-card__content">
          <div className="offer-card__heading">
            <div>
              <h3 className="offer-card__title">{offer.title}</h3>
              <div className="offer-card__meta">
                <span><Building2 size={14} /> {offer.company}</span>
                {offer.location ? <span><MapPin size={14} /> {offer.location}</span> : null}
                {offer.role ? <span><Briefcase size={14} /> {offer.role}</span> : null}
              </div>
            </div>
            <Badge tone="accent">Top #{offer.rank}</Badge>
          </div>

          <ProgressBar value={matchPercentage} label={`${matchPercentage}% ajuste`} />
          {offer.why_match ? <p className="offer-card__reason">{offer.why_match}</p> : null}

          {offer.matched_skills.length ? (
            <div className="offer-card__skills">
              {offer.matched_skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}
            </div>
          ) : null}
        </div>

        <div className="offer-card__actions">
          <Button size="sm" variant="secondary" icon={isSaved ? BookmarkCheck : Bookmark} onClick={onSave}>
            {isSaved ? "Guardada" : "Guardar"}
          </Button>
          {offer.url ? (
            <a href={offer.url} target="_blank" rel="noopener noreferrer" data-testid={`offer-link-${offer.id}`} className="nt-button nt-button--primary nt-button--sm">
              <ExternalLink size={13} /> <span>Ver oferta</span>
            </a>
          ) : null}
          <Button data-testid={`select-offer-${offer.id}`} size="sm" variant={isSelected ? "dark" : "secondary"} onClick={onSelect}>
            {isSelected ? "Seleccionada" : "Comparar"}
          </Button>
          <Button size="sm" variant="outline" icon={Compass} onClick={onCareerPlan}>Analizar brecha</Button>
          <Button size="sm" variant="dark" icon={Send} onClick={onApplication}>Candidatura</Button>
        </div>
      </div>

      <div className="offer-card__feedback">
        <span>¿Te resulta relevante?</span>
        <Button size="sm" variant={feedback === "positive" ? "secondary" : "ghost"} icon={ThumbsUp} onClick={() => onFeedback("positive")} aria-label={`Marcar ${offer.title} como relevante`}>Sí</Button>
        <Button size="sm" variant={feedback === "negative" ? "secondary" : "ghost"} icon={ThumbsDown} onClick={() => onFeedback("negative")} aria-label={`Marcar ${offer.title} como no relevante`}>No</Button>
      </div>
    </Card>
  );
}

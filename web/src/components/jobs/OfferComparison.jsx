import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

export function OfferComparison({ offers }) {
  return (
    <section data-testid="compare-view">
      <h2 className="font-serif text-3xl mb-6">Comparación de ofertas</h2>
      <div className="overflow-x-auto">
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${offers.length}, minmax(280px, 1fr))` }}>
          {offers.map((offer) => (
            <Card key={offer.id} data-testid={`compare-card-${offer.id}`}>
              <Badge className="mb-3">Top #{offer.rank}</Badge>
              <h3 className="font-serif text-xl mb-1">{offer.title}</h3>
              <p className="text-sm mb-4 text-[var(--olive-gray)]">{offer.company}</p>
              {[
                { label: "Ubicación", value: offer.location || "N/A" },
                { label: "Perfil", value: offer.role || "N/A" },
              ].map((row) => (
                <div key={row.label} className="flex justify-between gap-4 py-2 border-t border-[var(--border-cream)] text-xs">
                  <span className="text-[var(--stone-gray)]">{row.label}</span>
                  <span className="font-semibold text-right">{row.value}</span>
                </div>
              ))}
              {offer.matched_skills.length ? (
                <div className="mt-3">
                  <span className="text-xs text-[var(--stone-gray)]">Habilidades coincidentes</span>
                  <div className="flex flex-wrap gap-1 mt-2">{offer.matched_skills.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div>
                </div>
              ) : null}
              {offer.url ? (
                <a href={offer.url} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[var(--terracotta)]">
                  <ExternalLink size={12} /> Ver oferta original
                </a>
              ) : null}
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

import { Card } from "@/components/ui/Card";

export function MarketReading({ items }) {
  return (
    <Card>
      <div className="mb-5">
        <h2 className="font-serif text-2xl">Lectura del mercado</h2>
        <p className="text-sm mt-1 text-[var(--stone-gray)]">Interpretación automática del segmento que estás visualizando.</p>
      </div>
      {items.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {items.map((item) => (
            <Card key={item.label} tone="subtle">
              <div className="text-[11px] uppercase tracking-wide mb-2 text-[var(--stone-gray)] font-bold">{item.label}</div>
              <div className="font-serif text-xl">{item.value}</div>
              <p className="text-xs mt-3 text-[var(--olive-gray)]">{item.detail}</p>
            </Card>
          ))}
        </div>
      ) : (
        <div className="rounded-xl p-5 bg-[var(--parchment)] border border-dashed border-[var(--border-warm)]">
          <p className="text-sm text-[var(--stone-gray)]">No hay datos suficientes para generar una lectura del mercado con los filtros actuales.</p>
        </div>
      )}
    </Card>
  );
}

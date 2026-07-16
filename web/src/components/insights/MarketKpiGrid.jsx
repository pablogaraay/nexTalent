import { Card } from "@/components/ui/Card";

export function MarketKpiGrid({ items }) {
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 mb-8" aria-label="Indicadores del mercado">
      {items.map((item) => (
        <Card key={item.label} className="market-kpi">
          <div className="market-kpi__value">{item.value}</div>
          <div className="market-kpi__label">{item.label}</div>
          <p className="market-kpi__detail">{item.detail}</p>
        </Card>
      ))}
    </section>
  );
}

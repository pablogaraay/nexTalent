import ReactECharts from "echarts-for-react";

import { Card } from "@/components/ui/Card";

export function MarketChartPanel({ chartKey, events, metricLabel, option, resultCount }) {
  return (
    <Card elevated className="mb-8">
      <div className="flex items-center justify-between gap-4 mb-3">
        <h2 className="font-serif text-3xl">{metricLabel}</h2>
        <span className="text-xs text-[var(--stone-gray)] font-semibold">{resultCount} resultados</span>
      </div>
      {resultCount ? (
        <ReactECharts key={chartKey} notMerge option={option} className="market-chart" onEvents={events} />
      ) : (
        <div className="h-[340px] flex items-center justify-center rounded-xl bg-[var(--parchment)] border border-dashed border-[var(--border-warm)]">
          <p className="text-sm text-[var(--stone-gray)]">No hay datos para los filtros seleccionados.</p>
        </div>
      )}
    </Card>
  );
}

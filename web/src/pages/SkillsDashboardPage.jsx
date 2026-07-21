import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  BarChart3,
  Briefcase,
  ChevronDown,
  ChevronUp,
  Cpu,
  RefreshCw,
  SlidersHorizontal,
} from "lucide-react";
import { MarketChartPanel } from "@/components/insights/MarketChartPanel";
import { MarketKpiGrid } from "@/components/insights/MarketKpiGrid";
import { MarketReading } from "@/components/insights/MarketReading";
import { useMarketChartOption } from "@/components/insights/useMarketChartOption";
import { PageHeader } from "@/components/ui/PageHeader";
import { insightsAPI } from "@/lib/api";

function formatPct(value) {
  return Number(value || 0).toFixed(1);
}

export default function SkillsDashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [filtersOpen, setFiltersOpen] = useState(true);
  const [viewMode, setViewMode] = useState("skills");
  const [chartType, setChartType] = useState("bars");
  const [metricMode, setMetricMode] = useState("absolute");
  const [topN, setTopN] = useState(30);
  const [activeFilter, setActiveFilter] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [selectedCity, setSelectedCity] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("");
  const [selectedSeniority, setSelectedSeniority] = useState("");

  const fetchData = useCallback(() => {
    setLoading(true);
    setError("");

    insightsAPI.get({
      topN,
      company: selectedCompany,
      city: selectedCity,
      region: selectedRegion,
      seniority: selectedSeniority,
    })
      .then(({ data: resp }) => {
        if (resp?.error) {
          throw new Error(resp.error);
        }
        const result = resp.result || resp;
        setData(result);
      })
      .catch((err) => {
        setError(
          err.response?.data?.detail ||
          err.response?.data?.error ||
          err.message ||
          "Error cargando insights del mercado."
        );
      })
      .finally(() => {
        setLoading(false);
      });
  }, [selectedCity, selectedCompany, selectedRegion, selectedSeniority, topN]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const safeData = data || {};
  const topSkills = safeData.top_skills || [];
  const topTechnologies = safeData.top_technologies || [];
  const topJobs = safeData.top_jobs || [];
  const summary = safeData.summary || {};
  const availableFilters = safeData.available_filters || {};
  const appliedFilters = safeData.applied_filters || {};

  const metricField = metricMode === "share" ? "share_total_offers_pct" : "demand";
  const metricLabel = metricMode === "share" ? "% del total" : "Demanda";
  const metricSuffix = metricMode === "share" ? "%" : "";

  const baseRows = viewMode === "skills" ? topSkills : viewMode === "technologies" ? topTechnologies : topJobs;
  const idField = viewMode === "skills" ? "skill_id" : viewMode === "technologies" ? "technology_id" : "job_id";
  const labelField = viewMode === "skills" ? "skill_name" : viewMode === "technologies" ? "preferred_label" : "job_title";
  const companyOptions = availableFilters.companies || [];
  const cityOptions = availableFilters.cities || [];
  const regionOptions = availableFilters.regions || [];
  const seniorityOptions = availableFilters.seniorities || [];

  const filteredRows = useMemo(() => {
    let rows = [...baseRows];

    if (activeFilter && activeFilter.type === viewMode) {
      rows = rows.filter((row) => String(row[idField]) === String(activeFilter.id));
    }

    rows.sort((a, b) => Number(b.demand || 0) - Number(a.demand || 0));
    return rows;
  }, [activeFilter, baseRows, idField, viewMode]);

  const chartRows = filteredRows.slice(0, topN);

  const topSkill = topSkills[0] || null;
  const topTechnology = topTechnologies[0] || null;
  const topJob = topJobs[0] || null;
  const selectedFilterCount = [
    selectedCompany,
    selectedCity,
    selectedRegion,
    selectedSeniority,
  ].filter(Boolean).length;
  const careerTarget = activeFilter?.type === "jobs" ? activeFilter.label : topJob?.job_title;

  const kpis = [
    {
      label: "Ofertas filtradas",
      value: summary.filtered_offers || 0,
      detail: `${summary.total_offers || 0} en la base total`,
    },
    {
      label: "Perfiles clasificados",
      value: `${formatPct(summary.job_mapping_coverage_pct)}%`,
      detail: `${summary.offers_with_job_mapping || 0} ofertas con perfil identificado`,
    },
    {
      label: "Habilidades detectadas",
      value: `${formatPct(summary.skills_sfia_coverage_pct)}%`,
      detail: `${summary.offers_with_skills_sfia || 0} ofertas con habilidades identificadas`,
    },
    {
      label: "Tecnologías normalizadas",
      value: `${formatPct(summary.technologies_onet_coverage_pct)}%`,
      detail: `${summary.offers_with_technologies_onet || 0} ofertas con tecnologías O*NET`,
    },
    {
      label: "Habilidad principal",
      value: topSkill?.skill_name || "Sin datos",
      detail: topSkill ? `${topSkill.demand} ofertas` : "",
    },
    {
      label: "Tecnología principal",
      value: topTechnology?.preferred_label || "Sin datos",
      detail: topTechnology ? `${topTechnology.demand} ofertas` : "",
    },
    {
      label: "Perfil principal",
      value: topJob?.job_title || "Sin datos",
      detail: topJob ? `${topJob.demand} ofertas` : "",
    },
  ];

  const marketReading = useMemo(() => {
    if (!chartRows.length) {
      return [];
    }

    const totalFiltered = Number(summary.filtered_offers || 0);
    const leader = chartRows[0];
    const leaderLabel = leader?.[labelField] || "Sin datos";
    const leaderDemand = Number(leader?.demand || 0);
    const leaderShare = Number(leader?.share_total_offers_pct || 0);
    const top3Demand = chartRows.slice(0, 3).reduce((total, row) => total + Number(row.demand || 0), 0);
    const top3Share = totalFiltered > 0 ? (top3Demand / totalFiltered) * 100 : 0;
    const lowDemandThreshold = leaderDemand > 0 ? leaderDemand * 0.25 : 0;
    const lowDemandCount = chartRows.filter((row) => {
      const demand = Number(row.demand || 0);
      return demand > 0 && demand <= lowDemandThreshold;
    }).length;
    const coveragePct = viewMode === "skills"
      ? Number(summary.skills_sfia_coverage_pct || 0)
      : viewMode === "technologies"
        ? Number(summary.technologies_onet_coverage_pct || 0)
        : Number(summary.job_mapping_coverage_pct || 0);
    const itemSingular = viewMode === "skills" ? "habilidad" : viewMode === "technologies" ? "tecnología" : "perfil";
    const itemPlural = viewMode === "skills" ? "habilidades" : viewMode === "technologies" ? "tecnologías" : "perfiles";
    const concentrationLabel = top3Share >= 50 ? "Alta" : top3Share >= 30 ? "Media" : "Distribuida";

    return [
      {
        label: "Líder del ranking",
        value: leaderLabel,
        detail: `${leaderDemand} ofertas | ${formatPct(leaderShare)}% del segmento filtrado.`,
      },
      {
        label: "Concentración",
        value: concentrationLabel,
        detail: `El top 3 concentra ${formatPct(top3Share)}% de las ofertas filtradas.`,
      },
      {
        label: "Cola de demanda",
        value: `${lowDemandCount} ${itemPlural}`,
        detail: `Resultados con menos del 25% de la demanda del ${itemSingular} líder.`,
      },
      {
        label: "Consistencia de datos",
        value: `${formatPct(coveragePct)}%`,
        detail: "Porcentaje de ofertas con información suficiente para interpretar este segmento.",
      },
    ];
  }, [chartRows, labelField, summary, viewMode]);

  const chartOption = useMarketChartOption({
    chartRows,
    chartType,
    idField,
    labelField,
    metricField,
    metricLabel,
    metricSuffix,
  });

  const chartEvents = {
    click: (params) => {
      const dataPoint = params?.data || {};
      const id = dataPoint.id || dataPoint[idField];
      if (!id) return;
      setActiveFilter((prev) =>
        prev?.type === viewMode && String(prev.id) === String(id)
          ? null
          : { type: viewMode, id, label: dataPoint.name || "" }
      );
    },
  };

  const resetFilters = () => {
    setSelectedCompany("");
    setSelectedCity("");
    setSelectedRegion("");
    setSelectedSeniority("");
    setActiveFilter(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3" style={{ backgroundColor: "var(--parchment)" }}>
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--ring-warm)", borderTopColor: "transparent" }} />
        <p className="font-sans text-sm" style={{ color: "var(--stone-gray)" }}>
          Consultando base de datos de ofertas...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4" style={{ backgroundColor: "var(--parchment)" }}>
        <AlertCircle size={32} style={{ color: "var(--error-crimson)" }} />
        <p className="font-sans text-sm text-center" style={{ color: "var(--error-crimson)" }}>
          {error}
        </p>
        <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-sans" style={{ backgroundColor: "var(--terracotta)", color: "var(--ivory)", fontWeight: 500 }}>
          <RefreshCw size={14} /> Reintentar
        </button>
      </div>
    );
  }

  return (
    <div data-testid="skills-dashboard-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <PageHeader
          badge="Fuente: Base de datos"
          title="Habilidades, tecnologías y perfiles más demandados"
          description={`Análisis de ${summary.filtered_offers || 0} ofertas dentro de una base de ${summary.total_offers || 0}. Filtra, compara y descubre patrones.`}
          actions={careerTarget ? <Link to={`/career?targetRole=${encodeURIComponent(careerTarget)}`} className="nt-button nt-button--primary nt-button--md">Crear plan para {careerTarget}</Link> : null}
        />

        <MarketKpiGrid items={kpis} />

        <div className="rounded-2xl mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <div className="px-5 py-4 border-b flex items-start justify-between gap-4" style={{ borderColor: "var(--border-cream)" }}>
            <div>
              <button className="flex items-center gap-2" onClick={() => setFiltersOpen((prev) => !prev)}>
                <SlidersHorizontal size={16} style={{ color: "var(--stone-gray)" }} />
                <span className="font-sans text-sm" style={{ color: "var(--charcoal-warm)", fontWeight: 600 }}>
                  Explorar el mercado
                </span>
                {filtersOpen ? <ChevronUp size={16} style={{ color: "var(--stone-gray)" }} /> : <ChevronDown size={16} style={{ color: "var(--stone-gray)" }} />}
              </button>
              <p className="mt-2 font-sans text-xs sm:text-sm" style={{ color: "var(--stone-gray)", lineHeight: 1.5 }}>
                Primero elige qué parte del mercado quieres analizar y después decide cómo visualizar los resultados.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={fetchData}
                className="px-3 py-2 rounded-lg text-sm font-sans flex items-center gap-2"
                style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", fontWeight: 500 }}
                title="Actualizar datos"
              >
                <RefreshCw size={14} />
                Actualizar
              </button>
            </div>
          </div>

          {filtersOpen && (
            <div className="p-5">
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
                <div className="xl:col-span-6 rounded-2xl p-4" style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)" }}>
                  <div className="mb-4">
                    <p className="font-sans text-[11px] uppercase tracking-wide mb-1" style={{ color: "var(--terracotta)", fontWeight: 700 }}>
                      1. Filtrar mercado
                    </p>
                    <p className="font-sans text-sm" style={{ color: "var(--stone-gray)", lineHeight: 1.5 }}>
                      Estos filtros cambian la base de ofertas sobre la que calculamos los insights.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label className="block">
                      <span className="font-sans text-xs mb-1.5 block" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Empresa</span>
                      <select
                        value={selectedCompany}
                        onChange={(e) => setSelectedCompany(e.target.value)}
                        className="w-full rounded-lg px-3 py-2 text-sm font-sans"
                        style={{ backgroundColor: "var(--ivory)", color: "var(--charcoal-warm)", border: "1px solid var(--border-cream)" }}
                      >
                        <option value="">Todas las empresas</option>
                        {companyOptions.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.value} ({item.count})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="font-sans text-xs mb-1.5 block" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Ciudad</span>
                      <select
                        value={selectedCity}
                        onChange={(e) => setSelectedCity(e.target.value)}
                        className="w-full rounded-lg px-3 py-2 text-sm font-sans"
                        style={{ backgroundColor: "var(--ivory)", color: "var(--charcoal-warm)", border: "1px solid var(--border-cream)" }}
                      >
                        <option value="">Todas las ciudades</option>
                        {cityOptions.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.value} ({item.count})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="font-sans text-xs mb-1.5 block" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Región</span>
                      <select
                        value={selectedRegion}
                        onChange={(e) => setSelectedRegion(e.target.value)}
                        className="w-full rounded-lg px-3 py-2 text-sm font-sans"
                        style={{ backgroundColor: "var(--ivory)", color: "var(--charcoal-warm)", border: "1px solid var(--border-cream)" }}
                      >
                        <option value="">Todas las regiones</option>
                        {regionOptions.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.value} ({item.count})
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="font-sans text-xs mb-1.5 block" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Seniority</span>
                      <select
                        value={selectedSeniority}
                        onChange={(e) => setSelectedSeniority(e.target.value)}
                        className="w-full rounded-lg px-3 py-2 text-sm font-sans"
                        style={{ backgroundColor: "var(--ivory)", color: "var(--charcoal-warm)", border: "1px solid var(--border-cream)" }}
                      >
                        <option value="">Todos los niveles</option>
                        {seniorityOptions.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.value} ({item.count})
                          </option>
                        ))}
                      </select>
                    </label>

                  </div>
                </div>

                <div className="xl:col-span-6 rounded-2xl p-4" style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)" }}>
                  <div className="mb-4">
                    <p className="font-sans text-[11px] uppercase tracking-wide mb-1" style={{ color: "var(--terracotta)", fontWeight: 700 }}>
                      2. Ver resultados
                    </p>
                    <p className="font-sans text-sm" style={{ color: "var(--stone-gray)", lineHeight: 1.5 }}>
                      Estos controles no cambian la base de datos; solo la forma de explorarla.
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <p className="font-sans text-xs mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Vista</p>
                      <div className="flex flex-wrap gap-2">
                        {[
                          { key: "skills", label: "Habilidades", icon: BarChart3 },
                          { key: "technologies", label: "Tecnologías", icon: Cpu },
                          { key: "jobs", label: "Perfiles", icon: Briefcase },
                        ].map((item) => {
                          const Icon = item.icon;
                          const active = viewMode === item.key;
                          return (
                            <button
                              key={item.key}
                              onClick={() => {
                                setViewMode(item.key);
                                setActiveFilter(null);
                              }}
                              className="px-3 py-2 rounded-lg text-sm font-sans flex items-center gap-1.5"
                              style={{
                                backgroundColor: active ? "var(--near-black)" : "var(--ivory)",
                                color: active ? "var(--ivory)" : "var(--charcoal-warm)",
                                border: active ? "1px solid var(--near-black)" : "1px solid var(--border-cream)",
                                fontWeight: 500,
                              }}
                            >
                              <Icon size={14} />
                              {item.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <p className="font-sans text-xs mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Tipo de gráfico</p>
                      <div className="flex flex-wrap gap-2">
                        {[
                          { key: "bars", label: "Barras" },
                          { key: "horizontal", label: "Horizontal" },
                          { key: "line", label: "Línea" },
                          { key: "treemap", label: "Treemap" },
                          { key: "donut", label: "Donut" },
                        ].map((item) => (
                          <button
                            key={item.key}
                            onClick={() => setChartType(item.key)}
                            className="px-3 py-2 rounded-lg text-sm font-sans"
                            style={{
                              backgroundColor: chartType === item.key ? "var(--near-black)" : "var(--ivory)",
                              color: chartType === item.key ? "var(--ivory)" : "var(--charcoal-warm)",
                              border: chartType === item.key ? "1px solid var(--near-black)" : "1px solid var(--border-cream)",
                              fontWeight: 500,
                            }}
                          >
                            {item.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <p className="font-sans text-xs mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Métrica</p>
                        <div className="flex gap-2">
                          {[
                            { key: "absolute", label: "Absoluto" },
                            { key: "share", label: "%" },
                          ].map((item) => (
                            <button
                              key={item.key}
                              onClick={() => setMetricMode(item.key)}
                              className="px-3 py-2 rounded-lg text-sm font-sans"
                              style={{
                                backgroundColor: metricMode === item.key ? "var(--near-black)" : "var(--ivory)",
                                color: metricMode === item.key ? "var(--ivory)" : "var(--charcoal-warm)",
                                border: metricMode === item.key ? "1px solid var(--near-black)" : "1px solid var(--border-cream)",
                                fontWeight: 500,
                              }}
                            >
                              {item.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <label className="block">
                        <span className="font-sans text-xs mb-2 block" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Número de resultados</span>
                        <select
                          value={topN}
                          onChange={(e) => setTopN(Number(e.target.value))}
                          className="w-full rounded-lg px-3 py-2 text-sm font-sans"
                          style={{ backgroundColor: "var(--ivory)", color: "var(--charcoal-warm)", border: "1px solid var(--border-cream)" }}
                        >
                          {[10, 20, 30, 50, 75, 100].map((n) => (
                            <option key={n} value={n}>Top {n}</option>
                          ))}
                        </select>
                      </label>
                    </div>
                  </div>
                </div>

              </div>

              <div className="mt-4 flex items-center justify-between">
                <span className="font-sans text-xs" style={{ color: "var(--stone-gray)" }}>
                  {summary.filtered_offers || 0} ofertas tras segmentación
                </span>
                <div className="flex items-center gap-3">
                  {selectedFilterCount > 0 && (
                    <span className="text-xs font-sans px-3 py-1 rounded-full" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                      {selectedFilterCount} filtros de detalle activos
                    </span>
                  )}
                  {activeFilter && (
                    <span className="text-xs font-sans px-3 py-1 rounded-full" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                      Selección: {activeFilter.label}
                    </span>
                  )}
                  <button onClick={resetFilters} className="text-xs font-sans underline" style={{ color: "var(--terracotta)" }}>
                    Limpiar todo
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {selectedFilterCount > 0 && (
          <div className="flex flex-wrap gap-2 mb-8">
            {appliedFilters.company && (
              <span className="px-3 py-1.5 rounded-full text-xs font-sans" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                Empresa: {appliedFilters.company}
              </span>
            )}
            {appliedFilters.city && (
              <span className="px-3 py-1.5 rounded-full text-xs font-sans" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                Ciudad: {appliedFilters.city}
              </span>
            )}
            {appliedFilters.region && (
              <span className="px-3 py-1.5 rounded-full text-xs font-sans" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                Región: {appliedFilters.region}
              </span>
            )}
            {appliedFilters.seniority && (
              <span className="px-3 py-1.5 rounded-full text-xs font-sans" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                Seniority: {appliedFilters.seniority}
              </span>
            )}
          </div>
        )}

        <MarketChartPanel
          chartKey={`${viewMode}-${chartType}-${metricMode}`}
          events={chartEvents}
          metricLabel={`${viewMode === "skills" ? "Habilidades" : viewMode === "technologies" ? "Tecnologías" : "Perfiles"} · ${metricLabel}`}
          option={chartOption}
          resultCount={chartRows.length}
        />
        <MarketReading items={marketReading} />

      </div>
    </div>
  );
}

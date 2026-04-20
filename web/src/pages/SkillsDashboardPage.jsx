import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import {
  AlertCircle,
  BarChart3,
  Briefcase,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Search as SearchIcon,
  SlidersHorizontal,
} from "lucide-react";
import { insightsAPI } from "@/lib/api";

function formatPct(value) {
  return Number(value || 0).toFixed(1);
}

function includesText(value, query) {
  return (value || "").toLowerCase().includes((query || "").trim().toLowerCase());
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
  const [query, setQuery] = useState("");
  const [minDemand, setMinDemand] = useState(0);
  const [activeFilter, setActiveFilter] = useState(null);
  const [selectedFamilies, setSelectedFamilies] = useState([]);

  const fetchData = () => {
    setLoading(true);
    setError("");
    insightsAPI
      .get(topN)
      .then(({ data: resp }) => {
        const result = resp.result || resp;
        setData(result);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || err.response?.data?.error || "Error cargando insights del mercado.");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topN]);

  const safeData = data || {};
  const topSkills = safeData.top_skills || [];
  const topJobs = safeData.top_jobs || [];
  const summary = safeData.summary || {};

  const metricField = metricMode === "share" ? "share_total_offers_pct" : "demand";
  const metricLabel = metricMode === "share" ? "% del total" : "Demanda";
  const metricSuffix = metricMode === "share" ? "%" : "";

  const baseRows = viewMode === "skills" ? topSkills : topJobs;
  const idField = viewMode === "skills" ? "skill_id" : "job_id";
  const labelField = viewMode === "skills" ? "skill_name" : "job_title";

  const familyCounts = useMemo(() => {
    const counts = {};
    for (const row of topJobs) {
      const family = (row.job_family || "Sin familia").trim();
      counts[family] = (counts[family] || 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([family, count]) => ({ family, count }));
  }, [topJobs]);

  const maxDemandBase = Math.max(...baseRows.map((row) => Number(row.demand || 0)), 1);
  const minDemandSafe = Math.min(Number(minDemand || 0), maxDemandBase);

  const filteredRows = useMemo(() => {
    let rows = [...baseRows];

    if (activeFilter && activeFilter.type === viewMode) {
      rows = rows.filter((row) => String(row[idField]) === String(activeFilter.id));
    }

    if (query.trim()) {
      rows = rows.filter((row) => {
        const haystack =
          viewMode === "skills"
            ? `${row.skill_name || ""} ${row.skill_id || ""}`
            : `${row.job_title || ""} ${row.job_family || ""} ${row.job_id || ""}`;
        return includesText(haystack, query);
      });
    }

    if (viewMode === "jobs" && selectedFamilies.length) {
      rows = rows.filter((row) => selectedFamilies.includes(row.job_family || "Sin familia"));
    }

    rows = rows.filter((row) => Number(row.demand || 0) >= minDemandSafe);
    rows.sort((a, b) => Number(b.demand || 0) - Number(a.demand || 0));
    return rows;
  }, [activeFilter, baseRows, idField, minDemandSafe, query, selectedFamilies, viewMode]);

  const chartRows = filteredRows.slice(0, topN);

  const maxDemandFiltered = Math.max(...filteredRows.map((row) => Number(row.demand || 0)), 1);

  const valueFor = (row) => Number(row?.[metricField] || 0);
  const demandColorByRank = (i) => (i < 3 ? "#c96442" : i < 7 ? "#d97757" : "#87867f");

  const topSkill = topSkills[0] || null;
  const topJob = topJobs[0] || null;

  const kpis = [
    {
      label: "Ofertas analizadas",
      value: summary.total_offers || 0,
      detail: "Base total",
    },
    {
      label: "Job mapping",
      value: `${formatPct(summary.job_mapping_coverage_pct)}%`,
      detail: `${summary.offers_with_job_mapping || 0} ofertas`,
    },
    {
      label: "Skills SFIA",
      value: `${formatPct(summary.skills_sfia_coverage_pct)}%`,
      detail: `${summary.offers_with_skills_sfia || 0} ofertas`,
    },
    {
      label: "Top Skill",
      value: topSkill?.skill_name || "Sin datos",
      detail: topSkill ? `${topSkill.demand} ofertas` : "",
    },
    {
      label: "Top Job",
      value: topJob?.job_title || "Sin datos",
      detail: topJob ? `${topJob.demand} ofertas` : "",
    },
  ];

  const commonToolbox = {
    show: true,
    right: 8,
    top: 0,
    feature: {
      restore: {},
      saveAsImage: { name: "insights-nextalent" },
      dataView: { readOnly: true },
    },
    iconStyle: { borderColor: "#5e5d59" },
    emphasis: { iconStyle: { borderColor: "#c96442" } },
  };

  const chartOption = useMemo(() => {
    const categories = chartRows.map((row) => row[labelField] || "");
    const values = chartRows.map((row) => valueFor(row));

    const baseTooltip = {
      backgroundColor: "#141413",
      borderColor: "#30302e",
      textStyle: { color: "#faf9f5", fontFamily: "DM Sans" },
    };

    if (chartType === "horizontal") {
      return {
        tooltip: { ...baseTooltip, trigger: "axis", axisPointer: { type: "shadow" } },
        toolbox: commonToolbox,
        grid: { left: "24%", right: "5%", top: 50, bottom: 24 },
        xAxis: {
          type: "value",
          name: metricLabel,
          axisLabel: { color: "#5e5d59", fontFamily: "DM Sans" },
          splitLine: { lineStyle: { color: "#f0eee6" } },
        },
        yAxis: {
          type: "category",
          data: categories,
          axisLabel: {
            color: "#5e5d59",
            fontFamily: "DM Sans",
            formatter: (value) => (value.length > 28 ? `${value.slice(0, 28)}...` : value),
          },
          axisLine: { lineStyle: { color: "#e8e6dc" } },
        },
        series: [
          {
            type: "bar",
            data: chartRows.map((row, i) => ({
              value: valueFor(row),
              name: row[labelField],
              id: row[idField],
              itemStyle: { color: demandColorByRank(i), borderRadius: [0, 4, 4, 0] },
            })),
            barWidth: "55%",
          },
        ],
      };
    }

    if (chartType === "line") {
      return {
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          formatter: (params) => {
            const p = params?.[0];
            if (!p) return "";
            return `${p.name}<br/>${metricLabel}: ${p.value}${metricSuffix}`;
          },
        },
        toolbox: commonToolbox,
        grid: { left: "3%", right: "4%", bottom: "16%", containLabel: true },
        xAxis: {
          type: "category",
          data: categories,
          axisLabel: {
            color: "#5e5d59",
            fontFamily: "DM Sans",
            fontSize: 11,
            rotate: 35,
            formatter: (value) => (value.length > 28 ? `${value.slice(0, 28)}...` : value),
          },
          axisLine: { lineStyle: { color: "#e8e6dc" } },
        },
        yAxis: {
          type: "value",
          name: metricLabel,
          axisLabel: { color: "#5e5d59", fontFamily: "DM Sans" },
          splitLine: { lineStyle: { color: "#f0eee6" } },
        },
        dataZoom: [
          { type: "inside", xAxisIndex: 0, filterMode: "none" },
          { type: "slider", xAxisIndex: 0, height: 18, bottom: 8, borderColor: "#e8e6dc" },
        ],
        series: [
          {
            type: "line",
            smooth: true,
            symbolSize: 8,
            lineStyle: { width: 3, color: "#c96442" },
            itemStyle: { color: "#c96442" },
            data: chartRows.map((row) => ({ value: valueFor(row), name: row[labelField], id: row[idField] })),
          },
        ],
      };
    }

    if (chartType === "donut") {
      return {
        tooltip: {
          ...baseTooltip,
          trigger: "item",
          formatter: (param) => `${param.name}<br/>${metricLabel}: ${param.value}${metricSuffix}`,
        },
        toolbox: commonToolbox,
        legend: {
          type: "scroll",
          bottom: 4,
          textStyle: { color: "#5e5d59", fontFamily: "DM Sans", fontSize: 11 },
        },
        series: [
          {
            type: "pie",
            radius: ["34%", "64%"],
            center: ["50%", "42%"],
            itemStyle: { borderRadius: 6, borderColor: "#faf9f5", borderWidth: 3 },
            label: { show: true, color: "#4d4c48", fontFamily: "DM Sans", fontSize: 11 },
            data: chartRows.map((row, i) => ({
              value: valueFor(row),
              name: row[labelField],
              id: row[idField],
              itemStyle: { color: demandColorByRank(i) },
            })),
          },
        ],
      };
    }

    if (chartType === "treemap") {
      return {
        tooltip: {
          ...baseTooltip,
          trigger: "item",
          formatter: (param) => `${param.name}<br/>${metricLabel}: ${param.value}${metricSuffix}`,
        },
        toolbox: commonToolbox,
        series: [
          {
            type: "treemap",
            roam: true,
            nodeClick: "zoomToNode",
            breadcrumb: { show: false },
            label: {
              show: true,
              color: "#141413",
              formatter: "{b}",
              fontFamily: "DM Sans",
            },
            itemStyle: {
              borderColor: "#faf9f5",
              borderWidth: 2,
              gapWidth: 2,
            },
            data: chartRows.map((row, i) => ({
              name: row[labelField],
              value: valueFor(row),
              id: row[idField],
              itemStyle: { color: i < 3 ? "#c96442" : i < 7 ? "#d97757" : "#e8e6dc" },
            })),
          },
        ],
      };
    }

    return {
      tooltip: {
        ...baseTooltip,
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const p = params?.[0];
          if (!p) return "";
          return `${p.name}<br/>${metricLabel}: ${p.value}${metricSuffix}`;
        },
      },
      toolbox: commonToolbox,
      grid: { left: "3%", right: "4%", bottom: "16%", containLabel: true },
      xAxis: {
        type: "category",
        data: categories,
        axisLabel: {
          color: "#5e5d59",
          fontFamily: "DM Sans",
          fontSize: 11,
          rotate: 35,
          formatter: (value) => (value.length > 28 ? `${value.slice(0, 28)}...` : value),
        },
        axisLine: { lineStyle: { color: "#e8e6dc" } },
      },
      yAxis: {
        type: "value",
        name: metricLabel,
        axisLabel: { color: "#5e5d59", fontFamily: "DM Sans" },
        splitLine: { lineStyle: { color: "#f0eee6" } },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0, filterMode: "none" },
        { type: "slider", xAxisIndex: 0, height: 18, bottom: 8, borderColor: "#e8e6dc" },
      ],
      series: [
        {
          type: "bar",
          data: chartRows.map((row, i) => ({
            value: valueFor(row),
            name: row[labelField],
            id: row[idField],
            itemStyle: { color: demandColorByRank(i), borderRadius: [4, 4, 0, 0] },
          })),
          barWidth: "60%",
        },
      ],
    };
  }, [
    chartRows,
    chartType,
    commonToolbox,
    idField,
    labelField,
    metricLabel,
    metricSuffix,
    metricMode,
    valueFor,
  ]);

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

  const toggleFamily = (family) => {
    setSelectedFamilies((prev) =>
      prev.includes(family) ? prev.filter((item) => item !== family) : [...prev, family]
    );
  };

  const resetFilters = () => {
    setQuery("");
    setSelectedFamilies([]);
    setActiveFilter(null);
    setMinDemand(0);
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

  if (!data) return null;

  return (
    <div data-testid="skills-dashboard-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full" style={{ backgroundColor: "rgba(201,100,66,0.12)", color: "var(--terracotta)" }}>
          <span className="text-xs font-sans" style={{ fontWeight: 600 }}>Datos en vivo</span>
        </div>

        <div className="mb-10">
          <h1 className="font-serif mb-3" style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)", fontWeight: 500, lineHeight: 1.2, color: "var(--near-black)" }}>
            Skills y Jobs más demandados
          </h1>
          <p className="font-sans text-lg" style={{ color: "var(--olive-gray)", lineHeight: 1.6 }}>
            Análisis de {summary.total_offers || 0} ofertas reales del mercado. Filtra, compara y descubre patrones.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 mb-8">
          {kpis.map((stat) => (
            <div key={stat.label} className="p-4 rounded-xl" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
              <div className="font-serif" style={{ color: "var(--terracotta)", fontWeight: 500, fontSize: "1.45rem", lineHeight: 1.2 }}>
                {stat.value}
              </div>
              <div className="font-sans text-[11px] mt-2 uppercase tracking-wide" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>
                {stat.label}
              </div>
              <div className="font-sans text-xs mt-1" style={{ color: "var(--olive-gray)", lineHeight: 1.4 }}>
                {stat.detail}
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-2xl mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border-cream)" }}>
            <button className="flex items-center gap-2" onClick={() => setFiltersOpen((prev) => !prev)}>
              <SlidersHorizontal size={16} style={{ color: "var(--stone-gray)" }} />
              <span className="font-sans text-sm" style={{ color: "var(--charcoal-warm)", fontWeight: 600 }}>Filtros</span>
              {filtersOpen ? <ChevronUp size={16} style={{ color: "var(--stone-gray)" }} /> : <ChevronDown size={16} style={{ color: "var(--stone-gray)" }} />}
            </button>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ backgroundColor: "var(--warm-sand)" }}>
                <SearchIcon size={14} style={{ color: "var(--stone-gray)" }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={viewMode === "skills" ? "Buscar skill..." : "Buscar job o familia..."}
                  className="bg-transparent outline-none text-sm font-sans"
                  style={{ color: "var(--charcoal-warm)", width: "220px" }}
                />
              </div>

              <select
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="rounded-lg px-3 py-2 text-sm font-sans"
                style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
              >
                {[10, 20, 30, 50, 75, 100].map((n) => (
                  <option key={n} value={n}>Top {n}</option>
                ))}
              </select>

              <button
                onClick={fetchData}
                className="p-2 rounded-lg"
                style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}
                title="Actualizar"
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>

          {filtersOpen && (
            <div className="p-5">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
                <div>
                  <p className="font-sans text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Vista</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { key: "skills", label: "Skills", icon: BarChart3 },
                      { key: "jobs", label: "Jobs", icon: Briefcase },
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
                            backgroundColor: active ? "var(--near-black)" : "var(--warm-sand)",
                            color: active ? "var(--ivory)" : "var(--charcoal-warm)",
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
                  <p className="font-sans text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Gráfico</p>
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
                          backgroundColor: chartType === item.key ? "var(--near-black)" : "var(--warm-sand)",
                          color: chartType === item.key ? "var(--ivory)" : "var(--charcoal-warm)",
                          fontWeight: 500,
                        }}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="font-sans text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Métrica</p>
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
                          backgroundColor: metricMode === item.key ? "var(--near-black)" : "var(--warm-sand)",
                          color: metricMode === item.key ? "var(--ivory)" : "var(--charcoal-warm)",
                          fontWeight: 500,
                        }}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-sans text-[11px] uppercase tracking-wide" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>Demanda mínima</p>
                    <span className="font-sans text-xs" style={{ color: "var(--terracotta)", fontWeight: 600 }}>
                      {minDemandSafe}+
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={maxDemandBase}
                    value={minDemandSafe}
                    onChange={(e) => setMinDemand(Number(e.target.value))}
                    className="w-full"
                    style={{ accentColor: "#c96442" }}
                  />
                </div>
              </div>

              {viewMode === "jobs" && familyCounts.length > 0 && (
                <div className="mt-5">
                  <p className="font-sans text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--stone-gray)", fontWeight: 600 }}>
                    Familias profesionales
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {familyCounts.map(({ family, count }) => {
                      const active = selectedFamilies.includes(family);
                      return (
                        <button
                          key={family}
                          onClick={() => toggleFamily(family)}
                          className="px-3 py-1.5 rounded-full text-xs font-sans"
                          style={{
                            backgroundColor: active ? "var(--near-black)" : "var(--warm-sand)",
                            color: active ? "var(--ivory)" : "var(--charcoal-warm)",
                            fontWeight: 500,
                          }}
                        >
                          {family} <span style={{ opacity: 0.75 }}>({count})</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="mt-4 flex items-center justify-between">
                <span className="font-sans text-xs" style={{ color: "var(--stone-gray)" }}>
                  {filteredRows.length} coincidencias tras filtros
                </span>
                <div className="flex items-center gap-3">
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

        <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)", boxShadow: "rgba(0,0,0,0.05) 0px 4px 24px" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-serif" style={{ fontSize: "1.85rem", fontWeight: 500, color: "var(--near-black)" }}>
              {viewMode === "skills" ? "Skills" : "Jobs"} - {metricLabel}
            </h2>
            <span className="font-sans text-xs" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
              {chartRows.length} resultados
            </span>
          </div>

          {chartRows.length ? (
            <ReactECharts
              key={`${viewMode}-${chartType}-${metricMode}`}
              notMerge={true}
              option={chartOption}
              style={{ height: 420 }}
              onEvents={chartEvents}
            />
          ) : (
            <div className="h-[340px] flex items-center justify-center rounded-xl" style={{ backgroundColor: "var(--parchment)", border: "1px dashed var(--border-cream)" }}>
              <p className="font-sans text-sm" style={{ color: "var(--stone-gray)" }}>No hay datos para los filtros seleccionados.</p>
            </div>
          )}
        </div>

        <div className="rounded-2xl overflow-hidden" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <div className="p-5 border-b" style={{ borderColor: "var(--border-cream)" }}>
            <h3 className="font-serif" style={{ fontSize: "1.3rem", fontWeight: 500, color: "var(--near-black)" }}>
              {viewMode === "skills" ? "Detalle de Skills" : "Detalle de Jobs"}
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-cream)" }}>
                  {(viewMode === "skills"
                    ? ["#", "Skill", "Demanda", "%"]
                    : ["#", "Job", "Familia", "Demanda", "%"]
                  ).map((head) => (
                    <th key={head} className="text-left px-4 py-2.5 text-xs font-sans" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
                      {head}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chartRows.map((row, index) => (
                  <tr key={row[idField] || `${row[labelField]}-${index}`} style={{ borderBottom: "1px solid var(--border-cream)" }}>
                    <td className="px-4 py-2.5 text-xs font-sans" style={{ color: "var(--stone-gray)" }}>{index + 1}</td>
                    <td className="px-4 py-2.5">
                      <span className="font-sans text-sm" style={{ color: "var(--near-black)", fontWeight: 500 }}>
                        {row[labelField]}
                      </span>
                      {viewMode === "skills" && (
                        <span className="block text-xs font-sans" style={{ color: "var(--stone-gray)" }}>{row.skill_id}</span>
                      )}
                    </td>
                    {viewMode === "jobs" && (
                      <td className="px-4 py-2.5">
                        <span className="px-2 py-0.5 rounded-md text-xs font-sans" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                          {row.job_family}
                        </span>
                      </td>
                    )}
                    <td className="px-4 py-2.5 text-sm font-sans" style={{ color: "var(--olive-gray)" }}>{row.demand}</td>
                    <td className="px-4 py-2.5 text-sm font-sans" style={{ color: "var(--terracotta)", fontWeight: 500 }}>
                      {formatPct(row.share_total_offers_pct)}%
                    </td>
                  </tr>
                ))}
                {!chartRows.length && (
                  <tr>
                    <td colSpan={viewMode === "skills" ? 4 : 5} className="px-4 py-4 text-sm font-sans" style={{ color: "var(--stone-gray)" }}>
                      Sin resultados para los filtros actuales.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {data.generated_at_utc && (
          <p className="mt-6 text-xs font-sans text-center" style={{ color: "var(--stone-gray)" }}>
            Datos generados: {new Date(data.generated_at_utc).toLocaleString("es-ES")} | Colección: {data.collection}
          </p>
        )}
      </div>
    </div>
  );
}

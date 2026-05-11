import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import {
  AlertCircle,
  BarChart3,
  Briefcase,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  SlidersHorizontal,
} from "lucide-react";
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

  const fetchData = () => {
    setLoading(true);
    setError("");
    insightsAPI
      .get({
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
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topN, selectedCompany, selectedCity, selectedRegion, selectedSeniority]);

  const safeData = data || {};
  const topSkills = safeData.top_skills || [];
  const topJobs = safeData.top_jobs || [];
  const summary = safeData.summary || {};
  const availableFilters = safeData.available_filters || {};
  const appliedFilters = safeData.applied_filters || {};

  const metricField = metricMode === "share" ? "share_total_offers_pct" : "demand";
  const metricLabel = metricMode === "share" ? "% del total" : "Demanda";
  const metricSuffix = metricMode === "share" ? "%" : "";

  const baseRows = viewMode === "skills" ? topSkills : topJobs;
  const idField = viewMode === "skills" ? "skill_id" : "job_id";
  const labelField = viewMode === "skills" ? "skill_name" : "job_title";
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

  const maxDemandFiltered = Math.max(...filteredRows.map((row) => Number(row.demand || 0)), 1);

  const valueFor = (row) => Number(row?.[metricField] || 0);
  const demandColorByRank = (i) => (i < 3 ? "#c96442" : i < 7 ? "#d97757" : "#87867f");

  const topSkill = topSkills[0] || null;
  const topJob = topJobs[0] || null;
  const selectedFilterCount = [
    selectedCompany,
    selectedCity,
    selectedRegion,
    selectedSeniority,
  ].filter(Boolean).length;

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
      label: "Habilidad principal",
      value: topSkill?.skill_name || "Sin datos",
      detail: topSkill ? `${topSkill.demand} ofertas` : "",
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
      : Number(summary.job_mapping_coverage_pct || 0);
    const itemSingular = viewMode === "skills" ? "habilidad" : "perfil";
    const itemPlural = viewMode === "skills" ? "habilidades" : "perfiles";
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

  const commonToolbox = {
    show: true,
    right: 8,
    top: 0,
    feature: {
      restore: {},
      saveAsImage: { name: "insights-nextalent" },
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

  if (!data) return null;

  return (
    <div data-testid="skills-dashboard-page" className="min-h-screen" style={{ backgroundColor: "var(--parchment)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full" style={{ backgroundColor: "rgba(201,100,66,0.12)", color: "var(--terracotta)" }}>
          <span className="text-xs font-sans" style={{ fontWeight: 600 }}>Datos en vivo</span>
        </div>

        <div className="mb-10">
          <h1 className="font-serif mb-3" style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)", fontWeight: 500, lineHeight: 1.2, color: "var(--near-black)" }}>
            Habilidades y Perfiles más demandados
          </h1>
          <p className="font-sans text-lg" style={{ color: "var(--olive-gray)", lineHeight: 1.6 }}>
            Análisis de {summary.filtered_offers || 0} ofertas dentro de una base de {summary.total_offers || 0}. Filtra, compara y descubre patrones.
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

        <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)", boxShadow: "rgba(0,0,0,0.05) 0px 4px 24px" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-serif" style={{ fontSize: "1.85rem", fontWeight: 500, color: "var(--near-black)" }}>
              {viewMode === "skills" ? "Habilidades" : "Perfiles"} - {metricLabel}
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

        <div className="rounded-2xl p-6" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
          <div className="mb-5">
            <h3 className="font-serif" style={{ fontSize: "1.45rem", fontWeight: 500, color: "var(--near-black)" }}>
              Lectura del mercado
            </h3>
            <p className="font-sans text-sm mt-1" style={{ color: "var(--stone-gray)", lineHeight: 1.5 }}>
              Interpretación automática del segmento que estás visualizando.
            </p>
          </div>

          {marketReading.length ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {marketReading.map((item) => (
                <div key={item.label} className="p-4 rounded-xl" style={{ backgroundColor: "var(--parchment)", border: "1px solid var(--border-cream)" }}>
                  <div className="font-sans text-[11px] uppercase tracking-wide mb-2" style={{ color: "var(--stone-gray)", fontWeight: 700 }}>
                    {item.label}
                  </div>
                  <div className="font-serif" style={{ color: "var(--near-black)", fontWeight: 500, fontSize: "1.25rem", lineHeight: 1.25 }}>
                    {item.value}
                  </div>
                  <p className="font-sans text-xs mt-3" style={{ color: "var(--olive-gray)", lineHeight: 1.5 }}>
                    {item.detail}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl p-5" style={{ backgroundColor: "var(--parchment)", border: "1px dashed var(--border-cream)" }}>
              <p className="font-sans text-sm" style={{ color: "var(--stone-gray)" }}>
                No hay datos suficientes para generar una lectura del mercado con los filtros actuales.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

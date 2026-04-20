import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import { AlertCircle, BarChart3, Briefcase, RefreshCw } from "lucide-react";
import { insightsAPI } from "@/lib/api";

function sortRows(rows, sortBy, sortDir, type) {
  const direction = sortDir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    if (sortBy === "name") {
      const aName = type === "skill" ? a.skill_name || "" : a.job_title || "";
      const bName = type === "skill" ? b.skill_name || "" : b.job_title || "";
      return aName.localeCompare(bName, "es", { sensitivity: "base" }) * direction;
    }
    if (sortBy === "share") {
      return (Number(a.share_total_offers_pct || 0) - Number(b.share_total_offers_pct || 0)) * direction;
    }
    return (Number(a.demand || 0) - Number(b.demand || 0)) * direction;
  });
}

function formatPct(value) {
  return Number(value || 0).toFixed(1);
}

export default function SkillsDashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [chartView, setChartView] = useState("skills");
  const [topN, setTopN] = useState(20);
  const [metricMode, setMetricMode] = useState("absolute");
  const [activeFilter, setActiveFilter] = useState(null);
  const [skillSearch, setSkillSearch] = useState("");
  const [jobSearch, setJobSearch] = useState("");
  const [skillSortBy, setSkillSortBy] = useState("demand");
  const [skillSortDir, setSkillSortDir] = useState("desc");
  const [jobSortBy, setJobSortBy] = useState("demand");
  const [jobSortDir, setJobSortDir] = useState("desc");

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
  const metricLabel = metricMode === "share" ? "% del total de ofertas" : "Demanda (ofertas)";
  const metricSuffix = metricMode === "share" ? "%" : "";

  const valueFor = (row) => Number(row?.[metricField] || 0);
  const demandColorByRank = (i) => (i < 3 ? "#c96442" : i < 7 ? "#d97757" : "#87867f");
  const matchesText = (text, query) => (text || "").toLowerCase().includes((query || "").trim().toLowerCase());

  const skillsFiltered = useMemo(() => {
    let rows = [...topSkills];
    if (activeFilter?.type === "skill") {
      rows = rows.filter((row) => row.skill_id === activeFilter.id);
    }
    if (skillSearch.trim()) {
      rows = rows.filter((row) => matchesText(`${row.skill_name || ""} ${row.skill_id || ""}`, skillSearch));
    }
    return sortRows(rows, skillSortBy, skillSortDir, "skill");
  }, [topSkills, activeFilter, skillSearch, skillSortBy, skillSortDir]);

  const jobsFiltered = useMemo(() => {
    let rows = [...topJobs];
    if (activeFilter?.type === "job") {
      rows = rows.filter((row) => row.job_id === activeFilter.id);
    }
    if (jobSearch.trim()) {
      rows = rows.filter((row) => matchesText(`${row.job_title || ""} ${row.job_family || ""} ${row.job_id || ""}`, jobSearch));
    }
    return sortRows(rows, jobSortBy, jobSortDir, "job");
  }, [topJobs, activeFilter, jobSearch, jobSortBy, jobSortDir]);

  const maxSkillDemand = Math.max(...skillsFiltered.map((row) => Number(row.demand || 0)), 1);
  const maxJobDemand = Math.max(...jobsFiltered.map((row) => Number(row.demand || 0)), 1);

  const barWidthByMetric = (row, maxDemand) => {
    if (metricMode === "share") {
      return Math.min(Number(row.share_total_offers_pct || 0), 100);
    }
    return Math.min((Number(row.demand || 0) / maxDemand) * 100, 100);
  };

  const skillsChartRows = skillsFiltered;
  const jobsChartRows = jobsFiltered;
  const pieRows = skillsChartRows.slice(0, Math.min(skillsChartRows.length, 25));

  const topSkill = topSkills[0] || null;
  const topJob = topJobs[0] || null;
  const kpis = [
    {
      label: "Ofertas analizadas",
      value: summary.total_offers || 0,
      detail: "Base total actual"
    },
    {
      label: "Cobertura job mapping",
      value: `${formatPct(summary.job_mapping_coverage_pct)}%`,
      detail: `${summary.offers_with_job_mapping || 0} de ${summary.total_offers || 0}`
    },
    {
      label: "Cobertura skills SFIA",
      value: `${formatPct(summary.skills_sfia_coverage_pct)}%`,
      detail: `${summary.offers_with_skills_sfia || 0} de ${summary.total_offers || 0}`
    },
    {
      label: "Skill más demandada",
      value: topSkill?.skill_name || "Sin datos",
      detail: topSkill ? `${topSkill.demand} ofertas (${formatPct(topSkill.share_total_offers_pct)}%)` : ""
    },
    {
      label: "Job más demandado",
      value: topJob?.job_title || "Sin datos",
      detail: topJob ? `${topJob.demand} ofertas (${formatPct(topJob.share_total_offers_pct)}%)` : ""
    }
  ];

  const commonToolbox = {
    show: true,
    right: 10,
    top: 0,
    feature: {
      dataZoom: { yAxisIndex: "none" },
      restore: {},
      saveAsImage: { name: "insights-nextalent" },
      dataView: { readOnly: true },
    },
    iconStyle: { borderColor: "#5e5d59" },
    emphasis: { iconStyle: { borderColor: "#c96442" } },
  };

  const skillsBarOption = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#141413",
      borderColor: "#30302e",
      textStyle: { color: "#faf9f5", fontFamily: "DM Sans" },
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
      data: skillsChartRows.map((s) => s.skill_name),
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
      nameTextStyle: { color: "#87867f", fontFamily: "DM Sans" },
      axisLabel: { color: "#5e5d59", fontFamily: "DM Sans" },
      splitLine: { lineStyle: { color: "#f0eee6" } },
    },
    dataZoom: [
      { type: "inside", xAxisIndex: 0, filterMode: "none" },
      {
        type: "slider",
        xAxisIndex: 0,
        height: 18,
        bottom: 8,
        borderColor: "#e8e6dc",
        fillerColor: "rgba(201,100,66,0.15)",
        handleStyle: { color: "#c96442" },
      },
    ],
    series: [
      {
        type: "bar",
        data: skillsChartRows.map((s, i) => ({
          value: valueFor(s),
          name: s.skill_name,
          skill_id: s.skill_id,
          itemStyle: { color: demandColorByRank(i), borderRadius: [4, 4, 0, 0] },
        })),
        barWidth: "60%",
      },
    ],
  };

  const jobsBarOption = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "#141413",
      borderColor: "#30302e",
      textStyle: { color: "#faf9f5", fontFamily: "DM Sans" },
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
      data: jobsChartRows.map((j) => j.job_title),
      axisLabel: {
        color: "#5e5d59",
        fontFamily: "DM Sans",
        fontSize: 10,
        rotate: 35,
        formatter: (value) => (value.length > 28 ? `${value.slice(0, 28)}...` : value),
      },
      axisLine: { lineStyle: { color: "#e8e6dc" } },
    },
    yAxis: {
      type: "value",
      name: metricLabel,
      nameTextStyle: { color: "#87867f", fontFamily: "DM Sans" },
      axisLabel: { color: "#5e5d59", fontFamily: "DM Sans" },
      splitLine: { lineStyle: { color: "#f0eee6" } },
    },
    dataZoom: [
      { type: "inside", xAxisIndex: 0, filterMode: "none" },
      {
        type: "slider",
        xAxisIndex: 0,
        height: 18,
        bottom: 8,
        borderColor: "#e8e6dc",
        fillerColor: "rgba(201,100,66,0.15)",
        handleStyle: { color: "#c96442" },
      },
    ],
    series: [
      {
        type: "bar",
        data: jobsChartRows.map((j, i) => ({
          value: valueFor(j),
          name: j.job_title,
          job_id: j.job_id,
          itemStyle: { color: demandColorByRank(i), borderRadius: [4, 4, 0, 0] },
        })),
        barWidth: "60%",
      },
    ],
  };

  const skillsPieOption = {
    tooltip: {
      trigger: "item",
      backgroundColor: "#141413",
      borderColor: "#30302e",
      textStyle: { color: "#faf9f5", fontFamily: "DM Sans" },
      formatter: (param) => `${param.name}<br/>${metricLabel}: ${param.value}${metricSuffix}`,
    },
    toolbox: {
      ...commonToolbox,
      feature: {
        restore: {},
        saveAsImage: { name: "insights-nextalent-skills-pie" },
      },
    },
    legend: {
      type: "scroll",
      bottom: 4,
      textStyle: { color: "#5e5d59", fontFamily: "DM Sans", fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["30%", "62%"],
        center: ["50%", "42%"],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: "#faf9f5", borderWidth: 3 },
        label: { show: true, color: "#4d4c48", fontFamily: "DM Sans", fontSize: 11 },
        data: pieRows.map((s, i) => ({
          value: valueFor(s),
          name: s.skill_name,
          skill_id: s.skill_id,
          itemStyle: { color: demandColorByRank(i) },
        })),
      },
    ],
  };

  const chartEvents = {
    click: (params) => {
      if (!params?.data) return;
      if (chartView === "jobs") {
        const id = params.data.job_id;
        if (!id) return;
        setActiveFilter((prev) =>
          prev?.type === "job" && prev?.id === id ? null : { type: "job", id, label: params.data.name || "" }
        );
        return;
      }
      const id = params.data.skill_id;
      if (!id) return;
      setActiveFilter((prev) =>
        prev?.type === "skill" && prev?.id === id ? null : { type: "skill", id, label: params.data.name || "" }
      );
    },
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
        <div className="mb-10">
          <h1 className="font-serif mb-3" style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)", fontWeight: 500, lineHeight: 1.2, color: "var(--near-black)" }}>
            Skills y Jobs más demandados
          </h1>
          <p className="font-sans text-lg" style={{ color: "var(--olive-gray)", lineHeight: 1.6 }}>
            Datos reales de {summary.total_offers || 0} ofertas analizadas.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 mb-8">
          {kpis.map((stat) => (
            <div key={stat.label} className="p-4 rounded-xl" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
              <div className="font-serif" style={{ color: "var(--terracotta)", fontWeight: 500, fontSize: "1.45rem", lineHeight: 1.2 }}>
                {stat.value}
              </div>
              <div className="font-sans text-xs mt-2" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
                {stat.label}
              </div>
              <div className="font-sans text-xs mt-1" style={{ color: "var(--olive-gray)", lineHeight: 1.4 }}>
                {stat.detail}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <p className="font-sans text-xs mb-3" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
              Visualización del gráfico
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                { key: "skills", label: "Top Skills" },
                { key: "jobs", label: "Top Jobs" },
                { key: "pie", label: "Distribución Skills" },
              ].map((view) => (
                <button
                  key={view.key}
                  onClick={() => setChartView(view.key)}
                  className="px-4 py-2 rounded-lg text-sm font-sans transition-all"
                  style={{
                    backgroundColor: chartView === view.key ? "var(--near-black)" : "var(--warm-sand)",
                    color: chartView === view.key ? "var(--ivory)" : "var(--charcoal-warm)",
                    fontWeight: 500,
                  }}
                >
                  {view.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-3">
              <button
                onClick={() => setMetricMode("absolute")}
                className="px-3 py-1.5 rounded-lg text-xs font-sans"
                style={{
                  backgroundColor: metricMode === "absolute" ? "var(--near-black)" : "var(--warm-sand)",
                  color: metricMode === "absolute" ? "var(--ivory)" : "var(--charcoal-warm)",
                  fontWeight: 500,
                }}
              >
                Valor absoluto
              </button>
              <button
                onClick={() => setMetricMode("share")}
                className="px-3 py-1.5 rounded-lg text-xs font-sans"
                style={{
                  backgroundColor: metricMode === "share" ? "var(--near-black)" : "var(--warm-sand)",
                  color: metricMode === "share" ? "var(--ivory)" : "var(--charcoal-warm)",
                  fontWeight: 500,
                }}
              >
                Porcentaje
              </button>
            </div>
          </div>

          <div className="rounded-xl p-4" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <p className="font-sans text-xs mb-3" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
              Controles y filtros activos
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                Cantidad de resultados:
              </span>
              <select
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="rounded-lg px-2 py-1 text-sm font-sans"
                style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
              >
                {[10, 20, 30, 50, 75, 100].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
              <button
                onClick={fetchData}
                className="px-3 py-1.5 rounded-lg text-xs font-sans flex items-center gap-1"
                style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", fontWeight: 500 }}
              >
                <RefreshCw size={12} />
                Actualizar
              </button>
            </div>
            <div className="mt-3 min-h-6">
              {activeFilter ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-sans px-3 py-1.5 rounded-full" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                    {activeFilter.type === "skill" ? "Skill" : "Job"}: {activeFilter.label}
                  </span>
                  <button onClick={() => setActiveFilter(null)} className="text-xs font-sans underline" style={{ color: "var(--terracotta)" }}>
                    Limpiar
                  </button>
                </div>
              ) : (
                <span className="text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                  Sin filtros de selección activos.
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)", boxShadow: "rgba(0,0,0,0.05) 0px 4px 24px" }}>
          <ReactECharts
            key={`${chartView}-${metricMode}`}
            notMerge={true}
            option={chartView === "skills" ? skillsBarOption : chartView === "jobs" ? jobsBarOption : skillsPieOption}
            style={{ height: 420 }}
            onEvents={chartEvents}
          />
          <p className="mt-4 text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
            Haz clic en una barra o sector para filtrar. Usa la rueda o arrastra para hacer zoom horizontal.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-2xl overflow-hidden" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <div className="p-5 border-b" style={{ borderColor: "var(--border-cream)" }}>
              <h2 className="font-serif" style={{ fontSize: "1.3rem", fontWeight: 500, color: "var(--near-black)" }}>
                <BarChart3 size={18} className="inline mr-2" style={{ color: "var(--terracotta)" }} />
                Top Skills (SFIA)
              </h2>
              <div className="mt-3 flex flex-wrap gap-2">
                <input
                  value={skillSearch}
                  onChange={(e) => setSkillSearch(e.target.value)}
                  placeholder="Buscar skill..."
                  className="px-3 py-1.5 rounded-lg text-xs font-sans"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
                />
                <select
                  value={skillSortBy}
                  onChange={(e) => setSkillSortBy(e.target.value)}
                  className="px-2 py-1.5 rounded-lg text-xs font-sans"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
                >
                  <option value="demand">Ordenar por demanda</option>
                  <option value="share">Ordenar por porcentaje</option>
                  <option value="name">Ordenar por nombre</option>
                </select>
                <select
                  value={skillSortDir}
                  onChange={(e) => setSkillSortDir(e.target.value)}
                  className="px-2 py-1.5 rounded-lg text-xs font-sans"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
                >
                  <option value="desc">Descendente</option>
                  <option value="asc">Ascendente</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-cream)" }}>
                    {["#", "Skill", "Demanda", "%"].map((h) => (
                      <th key={h} className="text-left px-4 py-2.5 text-xs font-sans" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {skillsFiltered.map((skill, i) => (
                    <tr key={skill.skill_id || `${skill.skill_name}-${i}`} style={{ borderBottom: "1px solid var(--border-cream)" }}>
                      <td className="px-4 py-2.5 text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                        {i + 1}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="font-sans text-sm" style={{ color: "var(--near-black)", fontWeight: 500 }}>
                          {skill.skill_name}
                        </span>
                        <span className="block text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                          {skill.skill_id}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--border-cream)" }}>
                            <div className="h-full rounded-full" style={{ width: `${barWidthByMetric(skill, maxSkillDemand)}%`, backgroundColor: i < 3 ? "var(--terracotta)" : "var(--stone-gray)" }} />
                          </div>
                          <span className="text-xs font-sans" style={{ color: "var(--olive-gray)" }}>
                            {skill.demand}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-xs font-sans" style={{ color: "var(--terracotta)", fontWeight: 500 }}>
                        {skill.share_total_offers_pct}%
                      </td>
                    </tr>
                  ))}
                  {!skillsFiltered.length && (
                    <tr>
                      <td colSpan={4} className="px-4 py-4 text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                        No hay skills que coincidan con el filtro actual.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-2xl overflow-hidden" style={{ backgroundColor: "var(--ivory)", border: "1px solid var(--border-cream)" }}>
            <div className="p-5 border-b" style={{ borderColor: "var(--border-cream)" }}>
              <h2 className="font-serif" style={{ fontSize: "1.3rem", fontWeight: 500, color: "var(--near-black)" }}>
                <Briefcase size={18} className="inline mr-2" style={{ color: "var(--terracotta)" }} />
                Top Jobs (WEF)
              </h2>
              <div className="mt-3 flex flex-wrap gap-2">
                <input
                  value={jobSearch}
                  onChange={(e) => setJobSearch(e.target.value)}
                  placeholder="Buscar job o familia..."
                  className="px-3 py-1.5 rounded-lg text-xs font-sans"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
                />
                <select
                  value={jobSortBy}
                  onChange={(e) => setJobSortBy(e.target.value)}
                  className="px-2 py-1.5 rounded-lg text-xs font-sans"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
                >
                  <option value="demand">Ordenar por demanda</option>
                  <option value="share">Ordenar por porcentaje</option>
                  <option value="name">Ordenar por nombre</option>
                </select>
                <select
                  value={jobSortDir}
                  onChange={(e) => setJobSortDir(e.target.value)}
                  className="px-2 py-1.5 rounded-lg text-xs font-sans"
                  style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)", border: "none" }}
                >
                  <option value="desc">Descendente</option>
                  <option value="asc">Ascendente</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-cream)" }}>
                    {["#", "Job", "Familia", "Demanda", "%"].map((h) => (
                      <th key={h} className="text-left px-4 py-2.5 text-xs font-sans" style={{ color: "var(--stone-gray)", fontWeight: 500 }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {jobsFiltered.map((job, i) => (
                    <tr key={job.job_id || `${job.job_title}-${i}`} style={{ borderBottom: "1px solid var(--border-cream)" }}>
                      <td className="px-4 py-2.5 text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                        {i + 1}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="font-sans text-sm" style={{ color: "var(--near-black)", fontWeight: 500 }}>
                          {job.job_title}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="px-2 py-0.5 rounded-md text-xs font-sans" style={{ backgroundColor: "var(--warm-sand)", color: "var(--charcoal-warm)" }}>
                          {job.job_family}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--border-cream)" }}>
                            <div className="h-full rounded-full" style={{ width: `${barWidthByMetric(job, maxJobDemand)}%`, backgroundColor: i < 3 ? "var(--terracotta)" : "var(--stone-gray)" }} />
                          </div>
                          <span className="text-xs font-sans" style={{ color: "var(--olive-gray)" }}>
                            {job.demand}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-xs font-sans" style={{ color: "var(--terracotta)", fontWeight: 500 }}>
                        {job.share_total_offers_pct}%
                      </td>
                    </tr>
                  ))}
                  {!jobsFiltered.length && (
                    <tr>
                      <td colSpan={5} className="px-4 py-4 text-xs font-sans" style={{ color: "var(--stone-gray)" }}>
                        No hay jobs que coincidan con el filtro actual.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
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

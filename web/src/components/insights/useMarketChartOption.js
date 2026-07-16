import { useMemo } from "react";

const TOOLBOX = {
  show: true,
  right: 8,
  top: 0,
  feature: { restore: {}, saveAsImage: { name: "insights-nextalent" } },
  iconStyle: { borderColor: "#5e5d59" },
  emphasis: { iconStyle: { borderColor: "#c96442" } },
};

const TOOLTIP = {
  backgroundColor: "#141413",
  borderColor: "#30302e",
  textStyle: { color: "#faf9f5", fontFamily: "DM Sans" },
};

function colorByRank(index) {
  return index < 3 ? "#c96442" : index < 7 ? "#d97757" : "#87867f";
}

function truncateLabel(value) {
  return value.length > 28 ? `${value.slice(0, 28)}...` : value;
}

export function useMarketChartOption({ chartRows, chartType, idField, labelField, metricField, metricLabel, metricSuffix }) {
  return useMemo(() => {
    const categories = chartRows.map((row) => row[labelField] || "");
    const valueFor = (row) => Number(row?.[metricField] || 0);
    const seriesData = chartRows.map((row, index) => ({
      value: valueFor(row),
      name: row[labelField],
      id: row[idField],
      itemStyle: { color: colorByRank(index) },
    }));
    const valueAxis = {
      type: "value",
      name: metricLabel,
      axisLabel: { color: "#5e5d59", fontFamily: "DM Sans" },
      splitLine: { lineStyle: { color: "#f0eee6" } },
    };
    const categoryAxis = {
      type: "category",
      data: categories,
      axisLabel: { color: "#5e5d59", fontFamily: "DM Sans", fontSize: 11, rotate: 35, formatter: truncateLabel },
      axisLine: { lineStyle: { color: "#e8e6dc" } },
    };
    const tooltipFormatter = (params) => {
      const point = Array.isArray(params) ? params[0] : params;
      return point ? `${point.name}<br/>${metricLabel}: ${point.value}${metricSuffix}` : "";
    };

    if (chartType === "horizontal") {
      return {
        tooltip: { ...TOOLTIP, trigger: "axis", axisPointer: { type: "shadow" } },
        toolbox: TOOLBOX,
        grid: { left: "24%", right: "5%", top: 50, bottom: 24 },
        xAxis: valueAxis,
        yAxis: { ...categoryAxis, axisLabel: { ...categoryAxis.axisLabel, rotate: 0 } },
        series: [{ type: "bar", data: seriesData.map((item) => ({ ...item, itemStyle: { ...item.itemStyle, borderRadius: [0, 4, 4, 0] } })), barWidth: "55%" }],
      };
    }

    if (chartType === "line") {
      return {
        tooltip: { ...TOOLTIP, trigger: "axis", formatter: tooltipFormatter },
        toolbox: TOOLBOX,
        grid: { left: "3%", right: "4%", bottom: "16%", containLabel: true },
        xAxis: categoryAxis,
        yAxis: valueAxis,
        dataZoom: [{ type: "inside", xAxisIndex: 0, filterMode: "none" }, { type: "slider", xAxisIndex: 0, height: 18, bottom: 8, borderColor: "#e8e6dc" }],
        series: [{ type: "line", smooth: true, symbolSize: 8, lineStyle: { width: 3, color: "#c96442" }, itemStyle: { color: "#c96442" }, data: seriesData }],
      };
    }

    if (chartType === "donut") {
      return {
        tooltip: { ...TOOLTIP, trigger: "item", formatter: tooltipFormatter },
        toolbox: TOOLBOX,
        legend: { type: "scroll", bottom: 4, textStyle: { color: "#5e5d59", fontFamily: "DM Sans", fontSize: 11 } },
        series: [{ type: "pie", radius: ["34%", "64%"], center: ["50%", "42%"], itemStyle: { borderRadius: 6, borderColor: "#faf9f5", borderWidth: 3 }, label: { show: true, color: "#4d4c48", fontFamily: "DM Sans", fontSize: 11 }, data: seriesData }],
      };
    }

    if (chartType === "treemap") {
      return {
        tooltip: { ...TOOLTIP, trigger: "item", formatter: tooltipFormatter },
        toolbox: TOOLBOX,
        series: [{ type: "treemap", roam: true, nodeClick: "zoomToNode", breadcrumb: { show: false }, label: { show: true, color: "#141413", formatter: "{b}", fontFamily: "DM Sans" }, itemStyle: { borderColor: "#faf9f5", borderWidth: 2, gapWidth: 2 }, data: seriesData.map((item, index) => ({ ...item, itemStyle: { color: index < 3 ? "#c96442" : index < 7 ? "#d97757" : "#e8e6dc" } })) }],
      };
    }

    return {
      tooltip: { ...TOOLTIP, trigger: "axis", axisPointer: { type: "shadow" }, formatter: tooltipFormatter },
      toolbox: TOOLBOX,
      grid: { left: "3%", right: "4%", bottom: "16%", containLabel: true },
      xAxis: categoryAxis,
      yAxis: valueAxis,
      dataZoom: [{ type: "inside", xAxisIndex: 0, filterMode: "none" }, { type: "slider", xAxisIndex: 0, height: 18, bottom: 8, borderColor: "#e8e6dc" }],
      series: [{ type: "bar", data: seriesData.map((item) => ({ ...item, itemStyle: { ...item.itemStyle, borderRadius: [4, 4, 0, 0] } })), barWidth: "60%" }],
    };
  }, [chartRows, chartType, idField, labelField, metricField, metricLabel, metricSuffix]);
}

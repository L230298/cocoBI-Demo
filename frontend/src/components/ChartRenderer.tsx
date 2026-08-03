// 图表渲染 - ECharts + 表格切换 - PRD §3.4.4
import ReactECharts from 'echarts-for-react';
import { useState, useMemo } from 'react';
import { BarChart3, LineChart, PieChart, Table } from 'lucide-react';

type DisplayMode = 'bar' | 'line' | 'pie' | 'table';

interface Props {
  chartConfig: any;
}

export function ChartRenderer({ chartConfig }: Props) {
  const cfg = chartConfig?.config;
  const backendType = (chartConfig?.chart_type as DisplayMode) || 'bar';

  // 从后端给的 ECharts config 里把数据抽出来, 切换图表类型时复用
  const { labels, values, title } = useMemo(() => {
    if (!cfg) return { labels: [], values: [], title: '' };
    const xData = cfg.xAxis?.data || [];
    const seriesData = cfg.series?.[0]?.data || [];
    // pie 模式下 data 是 [{name, value}]; bar/line 是 number[]
    let labels: string[] = [];
    let values: number[] = [];
    if (xData.length) {
      labels = xData.map(String);
      values = seriesData.map((d: any) => (typeof d === 'number' ? d : d?.value ?? 0));
    } else if (Array.isArray(seriesData) && seriesData.length && typeof seriesData[0] === 'object') {
      // 无 xAxis (纯 pie): 从 [{name, value}] 拿
      labels = seriesData.map((d: any) => String(d.name));
      values = seriesData.map((d: any) => Number(d.value || 0));
    }
    return { labels, values, title: cfg.title?.text || '' };
  }, [cfg]);

  // 初始按后端推荐的类型
  const [mode, setMode] = useState<DisplayMode>(backendType);

  if (!cfg || !labels.length) {
    return <div className="chart-empty">暂无图表数据</div>;
  }

  // 构造不同模式下的 ECharts option
  const option = buildOption(mode, labels, values, title);

  return (
    <div className="chart-wrapper">
      <div className="chart-toolbar">
        <span className="chart-toolbar-label">视图:</span>
        <button
          className={`chart-tab ${mode === 'bar' ? 'active' : ''}`}
          onClick={() => setMode('bar')}
          title="柱状图"
        >
          <BarChart3 size={12} /> 柱状图
        </button>
        <button
          className={`chart-tab ${mode === 'line' ? 'active' : ''}`}
          onClick={() => setMode('line')}
          title="折线图"
        >
          <LineChart size={12} /> 折线图
        </button>
        <button
          className={`chart-tab ${mode === 'pie' ? 'active' : ''}`}
          onClick={() => setMode('pie')}
          title="饼图"
        >
          <PieChart size={12} /> 饼图
        </button>
        <button
          className={`chart-tab ${mode === 'table' ? 'active' : ''}`}
          onClick={() => setMode('table')}
          title="表格视图"
        >
          <Table size={12} /> 表格
        </button>
      </div>

      {mode === 'table' ? (
        <div className="chart-table-wrapper">
          <table className="chart-table">
            <thead>
              <tr>
                <th>#</th>
                <th>{title || '类目'}</th>
                <th style={{ textAlign: 'right' }}>数值</th>
              </tr>
            </thead>
            <tbody>
              {labels.map((label, i) => (
                <tr key={i}>
                  <td><code>{i + 1}</code></td>
                  <td>{label}</td>
                  <td style={{ textAlign: 'right' }}>{values[i].toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <ReactECharts
          key={mode}
          option={option}
          style={{ height: '320px', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
        />
      )}
    </div>
  );
}

function buildOption(mode: DisplayMode, labels: string[], values: number[], title: string) {
  if (mode === 'pie') {
    return {
      title: { text: title, left: 'center', textStyle: { fontSize: 16, fontWeight: 'bold' } },
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'horizontal', bottom: 0 },
      series: [
        {
          name: title || '占比',
          type: 'pie',
          radius: ['30%', '65%'],
          center: ['50%', '45%'],
          data: labels.map((name, i) => ({ name, value: values[i] })),
          label: { formatter: '{b}\n{d}%', fontSize: 11 },
        },
      ],
    };
  }

  // bar / line 共用 xAxis/yAxis 结构
  const isBar = mode === 'bar';
  return {
    title: { text: title, left: 'center', textStyle: { fontSize: 16, fontWeight: 'bold' } },
    tooltip: { trigger: 'axis', axisPointer: isBar ? { type: 'shadow' } : { type: 'line' } },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 0, interval: 0 } },
    yAxis: { type: 'value' },
    series: [
      {
        name: title || '数值',
        type: isBar ? 'bar' : 'line',
        data: values,
        label: { show: true, position: 'top', fontSize: 11, color: '#333', formatter: '{c}' },
        itemStyle: { color: isBar ? '#5470c6' : '#91cc75' },
        smooth: !isBar,
      },
    ],
  };
}
// 图表渲染 - ECharts - PRD §3.4.4 失败降级
import ReactECharts from 'echarts-for-react';

interface Props {
  chartConfig: any;
}

export function ChartRenderer({ chartConfig }: Props) {
  if (!chartConfig || !chartConfig.config) {
    return <div className="chart-empty">暂无图表数据</div>;
  }
  return (
    <div className="chart-wrapper">
      <ReactECharts
        option={chartConfig.config}
        style={{ height: '320px', width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
}

'use client';

import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  Tooltip,
  Bar,
  Cell,
  LabelList,
} from 'recharts';

type ContributionBarChartProps = {
  contributionComparisonData: Array<{ name: string; value: number | null }>;
  chartAxisColor: string;
  chartGridColor: string;
  chartMyBarColor: string;
  chartOthersBarColor: string;
  chartValueColor: string;
  chartTooltipBg: string;
  chartTooltipFg: string;
  chartTooltipBorder: string;
};

export function ContributionBarChart({
  contributionComparisonData,
  chartAxisColor,
  chartGridColor,
  chartMyBarColor,
  chartOthersBarColor,
  chartValueColor,
  chartTooltipBg,
  chartTooltipFg,
  chartTooltipBorder,
}: ContributionBarChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={contributionComparisonData} margin={{ top: 28, right: 12, left: 0, bottom: 12 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12, fill: chartAxisColor }}
          interval={0}
          axisLine={{ stroke: chartGridColor }}
          tickLine={{ stroke: chartGridColor }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: chartTooltipBg,
            borderColor: chartTooltipBorder,
            color: chartTooltipFg,
            borderRadius: '0.5rem',
            fontSize: '12px',
          }}
          itemStyle={{ color: chartTooltipFg }}
          labelStyle={{ color: chartTooltipFg }}
          formatter={(value: number | string) =>
            typeof value === 'number' ? [value.toFixed(1), '기여율 평균'] : ['-', '기여율 평균']
          }
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]} isAnimationActive animationDuration={700} animationEasing="ease-out">
          {contributionComparisonData.map((entry) => (
            <Cell key={entry.name} fill={entry.name === '나의 기여율 평균' ? chartMyBarColor : chartOthersBarColor} />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            offset={10}
            formatter={(value: number | string) =>
              typeof value === 'number' ? `${value.toFixed(1)}%` : String(value)
            }
            style={{ fill: chartValueColor, fontSize: 14, fontWeight: 700 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

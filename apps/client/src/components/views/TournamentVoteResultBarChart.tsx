'use client';

import dynamic from 'next/dynamic';

type TournamentVoteResultBarChartProps = {
  team1Name: string;
  team1Votes: number;
  team2Name: string;
  team2Votes: number;
};

const ChartImpl = dynamic<TournamentVoteResultBarChartProps>(
  async () => {
    const { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis } =
      await import('recharts');

    function Chart({ team1Name, team1Votes, team2Name, team2Votes }: TournamentVoteResultBarChartProps) {
      const data = [
        { name: team1Name, votes: team1Votes },
        { name: team2Name, votes: team2Votes },
      ];

      return (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 28, right: 12, left: 0, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12, fill: 'var(--color-muted-foreground)' }}
                interval={0}
                axisLine={{ stroke: 'var(--color-border)' }}
                tickLine={{ stroke: 'var(--color-border)' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--color-card)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-card-foreground)',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                }}
                itemStyle={{ color: 'var(--color-card-foreground)' }}
                labelStyle={{ color: 'var(--color-card-foreground)' }}
                formatter={(value: number | string) => [String(value), '득표수']}
              />
              <Bar dataKey="votes" radius={[8, 8, 0, 0]} isAnimationActive animationDuration={700} animationEasing="ease-out">
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={index === 0 ? 'var(--color-primary)' : 'var(--color-accent-500)'} />
                ))}
                <LabelList
                  dataKey="votes"
                  position="top"
                  offset={10}
                  formatter={(value: number | string) => String(value)}
                  style={{ fill: 'var(--color-foreground)', fontSize: 14, fontWeight: 700 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }

    return { default: Chart };
  },
  { ssr: false },
);

export function TournamentVoteResultBarChart(props: TournamentVoteResultBarChartProps) {
  return <ChartImpl {...props} />;
}

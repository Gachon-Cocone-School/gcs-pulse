'use client';

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis } from 'recharts';

type TournamentVoteResultBarChartProps = {
  team1Name: string;
  team1Votes: number;
  team2Name: string;
  team2Votes: number;
};

export function TournamentVoteResultBarChart({
  team1Name,
  team1Votes,
  team2Name,
  team2Votes,
}: TournamentVoteResultBarChartProps) {
  const data = [
    { name: team1Name, votes: team1Votes },
    { name: team2Name, votes: team2Votes },
  ];

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 28, right: 12, left: 0, bottom: 12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
            interval={0}
            axisLine={{ stroke: 'hsl(var(--border))' }}
            tickLine={{ stroke: 'hsl(var(--border))' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--popover))',
              borderColor: 'hsl(var(--border))',
              color: 'hsl(var(--popover-foreground))',
              borderRadius: '0.5rem',
              fontSize: '12px',
            }}
            itemStyle={{ color: 'hsl(var(--popover-foreground))' }}
            labelStyle={{ color: 'hsl(var(--popover-foreground))' }}
            formatter={(value: number | string) => [String(value), '득표수']}
          />
          <Bar dataKey="votes" radius={[8, 8, 0, 0]} isAnimationActive animationDuration={700} animationEasing="ease-out">
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={index === 0 ? 'hsl(var(--primary))' : 'hsl(var(--accent-2))'} />
            ))}
            <LabelList
              dataKey="votes"
              position="top"
              offset={10}
              formatter={(value: number | string) => String(value)}
              style={{ fill: 'hsl(var(--foreground))', fontSize: 14, fontWeight: 700 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

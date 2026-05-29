import { NeonStatCard, type NeonStatCardComponentProps } from "@/components/molecules/neon-stat-card";

export interface NeonStatsGridProps {
  cards: NeonStatCardComponentProps[];
}

export function NeonStatsGrid({ cards }: NeonStatsGridProps): React.ReactElement {
  return (
    <div
      className="grid gap-4"
      style={{
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
      }}
    >
      {cards.map((card) => (
        <NeonStatCard key={card.label} {...card} />
      ))}
    </div>
  );
}

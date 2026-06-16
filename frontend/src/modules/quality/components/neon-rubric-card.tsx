import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { NEON_CYAN, NEON_GREEN, TEXT, TEXT_MUTED } from "@/constants/neon";

export interface NeonRubricCardProps {
  title: string;
  category: string;
  score: number;
  maxScore?: number;
  criteria: string[];
}

export function NeonRubricCard({
  title,
  category,
  score,
  maxScore = 100,
  criteria,
}: NeonRubricCardProps): React.ReactElement {
  const percent = Math.round((score / maxScore) * 100);
  const scoreColor = percent >= 70 ? NEON_GREEN : NEON_CYAN;

  return (
    <NeonCard hover padding="md" accent="cyan">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-bold" style={{ color: TEXT }}>
            {title}
          </h3>
          <NeonBadge variant="amber" size="sm" className="mt-1">
            {category}
          </NeonBadge>
        </div>
        <span className="text-2xl font-bold" style={{ color: scoreColor }}>
          {score}
        </span>
      </div>
      <ul className="space-y-1">
        {criteria.map((criterion) => (
          <li key={criterion} className="text-xs" style={{ color: TEXT_MUTED }}>
            · {criterion}
          </li>
        ))}
      </ul>
    </NeonCard>
  );
}

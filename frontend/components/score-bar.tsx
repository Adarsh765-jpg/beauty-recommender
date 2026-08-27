type ScoreBarProps = {
  label: string;
  rawScore: number;
};

export function ScoreBar({ label, rawScore }: ScoreBarProps) {
  const percent = Math.round(rawScore * 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-body">{label}</span>
        <span className="font-semibold tabular-nums text-foreground">{percent}%</span>
      </div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${Math.max(4, percent)}%` }} />
      </div>
    </div>
  );
}

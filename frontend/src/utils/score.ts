export function formatRelevance(score: number | null | undefined): string {
  const numericScore = Number(score);
  if (!Number.isFinite(numericScore)) {
    return "N/A";
  }

  const normalized = numericScore >= -1 && numericScore <= 1
    ? (numericScore + 1) / 2
    : numericScore / 100;

  const percent = Math.max(0, Math.min(100, normalized * 100));
  return `${percent.toFixed(1)}%`;
}

export function formatRawScore(score: number | null | undefined): string {
  const numericScore = Number(score);
  if (!Number.isFinite(numericScore)) {
    return "N/A";
  }
  return numericScore.toFixed(6);
}

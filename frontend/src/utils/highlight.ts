export type HighlightSegment = {
  text: string;
  matched: boolean;
};

export function buildHighlightSegments(content: string, query: string): HighlightSegment[] {
  const source = content ?? "";
  const needle = query.trim();

  if (!needle) {
    return [{ text: source, matched: false }];
  }

  const lowerSource = source.toLowerCase();
  const lowerNeedle = needle.toLowerCase();

  const segments: HighlightSegment[] = [];
  let cursor = 0;

  while (cursor < source.length) {
    const index = lowerSource.indexOf(lowerNeedle, cursor);

    if (index < 0) {
      segments.push({ text: source.slice(cursor), matched: false });
      break;
    }

    if (index > cursor) {
      segments.push({ text: source.slice(cursor, index), matched: false });
    }

    segments.push({ text: source.slice(index, index + needle.length), matched: true });
    cursor = index + needle.length;
  }

  return segments.length > 0 ? segments : [{ text: source, matched: false }];
}

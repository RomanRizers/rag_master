import { buildHighlightSegments } from "../utils/highlight";

type HighlightTextProps = {
  text: string;
  query: string;
  noContentLabel: string;
};

export function HighlightText({ text, query, noContentLabel }: HighlightTextProps) {
  const content = text?.trim() ? text : noContentLabel;
  const segments = buildHighlightSegments(content, query);

  return (
    <>
      {segments.map((segment, index) =>
        segment.matched ? (
          <mark className="text-highlight" key={`${index}-${segment.text}`}>
            {segment.text}
          </mark>
        ) : (
          <span key={`${index}-${segment.text}`}>{segment.text}</span>
        )
      )}
    </>
  );
}

import type { AppErrorCopy } from "../utils/appError";
import { resolveAppError } from "../utils/appError";

type ErrorBannerProps = {
  error: unknown;
  copy: AppErrorCopy;
  className: string;
};

export function ErrorBanner({ error, copy, className }: ErrorBannerProps) {
  const resolved = resolveAppError(error, copy);

  return (
    <p className={className} role="alert">
      <strong>{resolved.title}</strong>
      {resolved.code ? ` (${resolved.code})` : ""}: {resolved.message}
    </p>
  );
}

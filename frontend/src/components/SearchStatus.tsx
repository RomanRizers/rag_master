import type { AppErrorCopy } from "../utils/appError";
import { ErrorBanner } from "./ErrorBanner";

type SearchStatusCopy = {
  loading: string;
  empty: string;
  found: string;
};

type SearchStatusProps = {
  loading: boolean;
  isError: boolean;
  error: unknown;
  isSuccess: boolean;
  total: number;
  visible: number;
  text: SearchStatusCopy;
  errorCopy: AppErrorCopy;
};

export function SearchStatus({
  loading,
  isError,
  error,
  isSuccess,
  total,
  visible,
  text,
  errorCopy
}: SearchStatusProps) {
  if (loading) {
    return (
      <div className="skeleton-grid" aria-live="polite" aria-busy="true" aria-label={text.loading}>
        <div className="skeleton-card" />
        <div className="skeleton-card" />
        <div className="skeleton-card" />
      </div>
    );
  }

  if (isError) {
    return <ErrorBanner error={error} copy={errorCopy} className="status status-error" />;
  }

  if (isSuccess && total === 0) {
    return <p className="status">{text.empty}</p>;
  }

  if (isSuccess) {
    return (
      <p className="status">
        {text.found}: {visible} / {total}
      </p>
    );
  }

  return null;
}

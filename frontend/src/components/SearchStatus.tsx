type SearchStatusCopy = {
  loading: string;
  empty: string;
  errorPrefix: string;
  found: string;
};

type SearchStatusProps = {
  loading: boolean;
  isError: boolean;
  errorMessage: string;
  isSuccess: boolean;
  total: number;
  visible: number;
  text: SearchStatusCopy;
};

export function SearchStatus({
  loading,
  isError,
  errorMessage,
  isSuccess,
  total,
  visible,
  text
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
    return (
      <p className="status status-error" role="alert">
        {text.errorPrefix}: {errorMessage}
      </p>
    );
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

type ConfirmModalProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "danger" | "default";
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel = "Отмена",
  tone = "danger",
  pending = false,
  onConfirm,
  onCancel
}: ConfirmModalProps) {
  if (!open) {
    return null;
  }

  return (
    <>
      <button type="button" aria-label={cancelLabel} className="modal-backdrop" onClick={onCancel} />
      <section className="confirm-modal panel" aria-modal="true" role="dialog" aria-label={title}>
        <div className="panel-head">
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <div className="confirm-modal-actions">
          <button type="button" className="ghost-button" onClick={onCancel} disabled={pending}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={tone === "danger" ? "danger-action" : "primary-action"}
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? "Подтверждение..." : confirmLabel}
          </button>
        </div>
      </section>
    </>
  );
}

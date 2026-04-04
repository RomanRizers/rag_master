import { ApiRequestError } from "../api/client";

export type AppErrorCopy = {
  genericTitle: string;
  genericMessage: string;
  llmUnavailableTitle: string;
  llmUnavailableMessage: string;
  retrievalFailedTitle: string;
  retrievalFailedMessage: string;
  parsingFailedTitle: string;
  parsingFailedMessage: string;
  embeddingFailedTitle: string;
  embeddingFailedMessage: string;
  rateLimitedTitle: string;
  rateLimitedMessage: string;
  fileTooLargeTitle: string;
  fileTooLargeMessage: string;
  invalidFileTypeTitle: string;
  invalidFileTypeMessage: string;
};

export type ResolvedAppError = {
  title: string;
  message: string;
  code?: string;
};

export const appErrorCopy = {
  ru: {
    genericTitle: "Ошибка",
    genericMessage: "Произошла непредвиденная ошибка.",
    llmUnavailableTitle: "LLM недоступна",
    llmUnavailableMessage: "Проверьте настройки провайдера и readiness backend.",
    retrievalFailedTitle: "Сбой поиска контекста",
    retrievalFailedMessage: "Не удалось получить релевантные фрагменты из индекса.",
    parsingFailedTitle: "Документ не обработан",
    parsingFailedMessage: "Парсинг файла завершился ошибкой. Проверьте формат и содержимое.",
    embeddingFailedTitle: "Сбой индексации embeddings",
    embeddingFailedMessage: "Векторизация документа завершилась ошибкой.",
    rateLimitedTitle: "Слишком много запросов",
    rateLimitedMessage: "Повторите попытку немного позже.",
    fileTooLargeTitle: "Файл слишком большой",
    fileTooLargeMessage: "Уменьшите размер файла или поднимите лимит загрузки.",
    invalidFileTypeTitle: "Неподдерживаемый формат файла",
    invalidFileTypeMessage: "Допустимы только PDF, DOCX и TXT."
  },
  en: {
    genericTitle: "Error",
    genericMessage: "An unexpected error occurred.",
    llmUnavailableTitle: "LLM unavailable",
    llmUnavailableMessage: "Check provider configuration and backend readiness.",
    retrievalFailedTitle: "Context retrieval failed",
    retrievalFailedMessage: "The app could not fetch relevant snippets from the index.",
    parsingFailedTitle: "Document parsing failed",
    parsingFailedMessage: "The uploaded file could not be parsed. Check its format and content.",
    embeddingFailedTitle: "Embedding indexing failed",
    embeddingFailedMessage: "Document vectorization failed during indexing.",
    rateLimitedTitle: "Too many requests",
    rateLimitedMessage: "Try again in a moment.",
    fileTooLargeTitle: "File too large",
    fileTooLargeMessage: "Reduce the file size or raise the upload limit.",
    invalidFileTypeTitle: "Unsupported file type",
    invalidFileTypeMessage: "Only PDF, DOCX, and TXT are accepted."
  }
} satisfies Record<"ru" | "en", AppErrorCopy>;

export function resolveAppError(error: unknown, copy: AppErrorCopy): ResolvedAppError {
  if (error instanceof ApiRequestError) {
    switch (error.code) {
      case "llm_unavailable":
        return { title: copy.llmUnavailableTitle, message: copy.llmUnavailableMessage, code: error.code };
      case "retrieval_failed":
        return { title: copy.retrievalFailedTitle, message: copy.retrievalFailedMessage, code: error.code };
      case "parsing_failed":
        return { title: copy.parsingFailedTitle, message: copy.parsingFailedMessage, code: error.code };
      case "embedding_failed":
        return { title: copy.embeddingFailedTitle, message: copy.embeddingFailedMessage, code: error.code };
      case "rate_limited":
        return { title: copy.rateLimitedTitle, message: copy.rateLimitedMessage, code: error.code };
      case "file_too_large":
        return { title: copy.fileTooLargeTitle, message: copy.fileTooLargeMessage, code: error.code };
      case "invalid_file_type":
        return { title: copy.invalidFileTypeTitle, message: copy.invalidFileTypeMessage, code: error.code };
      default:
        return {
          title: copy.genericTitle,
          message: error.message || copy.genericMessage,
          code: error.code
        };
    }
  }

  if (error instanceof Error) {
    return {
      title: copy.genericTitle,
      message: error.message || copy.genericMessage
    };
  }

  return {
    title: copy.genericTitle,
    message: copy.genericMessage
  };
}

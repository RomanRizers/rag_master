export type Language = "ru" | "en";

export type Copy = {
  // Search page (existing)
  title: string;
  subtitle: string;
  queryPlaceholder: string;
  topKLabel: string;
  topKHint: string;
  searchButton: string;
  loading: string;
  empty: string;
  found: string;
  relevance: string;
  rawScore: string;
  knowledgeBase: string;
  content: string;
  keywords: string;
  noContent: string;
  noKeywords: string;
  errorPrefix: string;
  unexpectedError: string;
  sortLabel: string;
  filterLabel: string;
  clearFilters: string;
  sortRelevanceDesc: string;
  sortRelevanceAsc: string;
  sortContentLengthDesc: string;
  sortContentLengthAsc: string;
  copyContent: string;
  copyKeywords: string;
  copied: string;
  themeLabel: string;
  themeLight: string;
  themeDark: string;
  themeSystem: string;

  // App header
  ragWorkspace: string;

  // Chat page
  chatSessions: string;
  chatDialogues: string;
  chatNewSession: string;
  chatNoSessions: string;
  chatConversation: string;
  chatSelectSession: string;
  chatClear: string;
  chatClearConfirm: string;
  chatClearYes: string;
  chatClearCancel: string;
  chatAllKBs: string;
  chatSelectKBs: string;
  chatEmptyTitle: string;
  chatEmptyHint: string;
  chatSuggestion1: string;
  chatSuggestion2: string;
  chatSuggestion3: string;
  chatYou: string;
  chatAssistant: string;
  chatSources: string;
  chatPlaceholder: string;
  chatParams: string;
  chatKBs: string;
  chatSend: string;
  chatSending: string;
  chatThinking: string;
  chatTyping: string;
  kbModalTitle: string;
  kbModalHintAll: string;
  kbModalHintSelected: string;
  kbModalEmpty: string;
  kbModalReset: string;
  kbModalApply: string;
  kbDoc: string;
  msgSessionMissing: string;
  msgMessageRequired: string;
  justNow: string;
  minAgo: string;
  hoursAgo: string;
  sessMsg: string;

  // Dataset page
  datasetTitle: string;
  datasetSubtitle: string;
  datasetCreate: string;
  datasetFiles: string;
  datasetBack: string;
  datasetAllBases: string;
  datasetShow: string;
  datasetPrev: string;
  datasetNext: string;
  datasetPage: string;
  datasetRename: string;
  datasetDelete: string;
  datasetRenamePlaceholder: string;
  datasetTotalDocs: string;
  datasetIndexed: string;
  datasetPending: string;
  datasetChunkSize: string;
  datasetAddDoc: string;
  datasetAddDocHint: string;
  datasetFile: string;
  datasetSourceName: string;
  datasetSourcePlaceholder: string;
  datasetTags: string;
  datasetUpload: string;
  datasetUploading: string;
  datasetRecentJobs: string;
  datasetRecentJobsHint: string;
  datasetNoJobs: string;
  datasetDocuments: string;
  datasetDocumentsHint: string;
  datasetNoDocuments: string;
  datasetIndexing: string;
  datasetIndexInProgress: string;
  datasetDeleteDoc: string;
  datasetKeywordsAfterIndex: string;
  datasetDetailHint: string;
  datasetNotFound: string;
  datasetDocumentNotFound: string;
  datasetChunks: string;
  datasetChunksHint: string;
  datasetChunkSearch: string;
  datasetLoadingChunks: string;
  datasetNoChunks: string;
  datasetStatus: string;
  datasetSource: string;
  datasetChunkKeywords: string;
  datasetKBSettings: string;
  datasetKBSettingsHint: string;
  datasetPreset: string;
  datasetChunkSizeLabel: string;
  datasetOverlap: string;
  datasetKeywordsPerChunk: string;
  datasetReindex: string;
  datasetReindexing: string;
  datasetSaveSettings: string;
  datasetSaving: string;
  datasetCreateTitle: string;
  datasetNameLabel: string;
  datasetNamePlaceholder: string;
  datasetCancel: string;
  datasetCreating: string;
  datasetDeleteConfirm: string;
  datasetPage404: string;
  datasetTokens: string;
  datasetKwChunk: string;
  datasetDelimiters: string;
  datasetDelimitersPlaceholder: string;
  datasetUploadDocs: string;
  datasetDropFiles: string;
  datasetUploadAll: string;
};

export const copy: Record<Language, Copy> = {
  ru: {
    // Search
    title: "Поиск фрагментов",
    subtitle: "Семантический поиск по документам с быстрым просмотром релевантных фрагментов",
    queryPlaceholder: "Введите запрос",
    topKLabel: "Результатов",
    topKHint: "Количество результатов (1-50)",
    searchButton: "Найти",
    loading: "Идёт поиск...",
    empty: "Ничего не найдено",
    found: "Показано результатов",
    relevance: "Релевантность",
    rawScore: "Raw score",
    knowledgeBase: "База знаний",
    content: "Контент",
    keywords: "Ключевые слова",
    noContent: "Контент отсутствует",
    noKeywords: "Ключевые слова отсутствуют",
    errorPrefix: "Ошибка",
    unexpectedError: "Непредвиденная ошибка",
    sortLabel: "Сортировка",
    filterLabel: "Фильтр по ключевым словам",
    clearFilters: "Сбросить",
    sortRelevanceDesc: "Сначала самые релевантные",
    sortRelevanceAsc: "Сначала наименее релевантные",
    sortContentLengthDesc: "Сначала длинные фрагменты",
    sortContentLengthAsc: "Сначала короткие фрагменты",
    copyContent: "Копировать контент",
    copyKeywords: "Копировать ключевые слова",
    copied: "Скопировано",
    themeLabel: "Тема",
    themeLight: "Светлая",
    themeDark: "Тёмная",
    themeSystem: "Системная",
    // App
    ragWorkspace: "RAG рабочее пространство",
    // Chat
    chatSessions: "Сессии",
    chatDialogues: "Диалоги",
    chatNewSession: "Новая сессия",
    chatNoSessions: "Нет сессий. Создайте первую.",
    chatConversation: "Диалог",
    chatSelectSession: "Выберите сессию",
    chatClear: "Очистить",
    chatClearConfirm: "Удалить диалог?",
    chatClearYes: "Да",
    chatClearCancel: "Отмена",
    chatAllKBs: "Все KB",
    chatSelectKBs: "Выбрать базы знаний",
    chatEmptyTitle: "Начните диалог",
    chatEmptyHint: "Напишите вопрос по загруженным документам.",
    chatSuggestion1: "Что такое RAG?",
    chatSuggestion2: "Какие документы загружены?",
    chatSuggestion3: "Сделай краткое саммари",
    chatYou: "Вы",
    chatAssistant: "Ассистент",
    chatSources: "Источники",
    chatPlaceholder: "Сформулируйте вопрос по документам...",
    chatParams: "Параметры",
    chatKBs: "Базы знаний",
    chatSend: "Отправить",
    chatSending: "Отправка...",
    chatThinking: "Думаю...",
    chatTyping: "Печатает...",
    kbModalTitle: "Базы знаний",
    kbModalHintAll: "Поиск идёт по всем базам знаний.",
    kbModalHintSelected: "Выбрано {n} из {total}.",
    kbModalEmpty: "Базы знаний не найдены",
    kbModalReset: "Сбросить",
    kbModalApply: "Применить",
    kbDoc: "doc",
    msgSessionMissing: "Сначала выберите или создайте сессию",
    msgMessageRequired: "Введите сообщение",
    justNow: "только что",
    minAgo: "мин назад",
    hoursAgo: "ч назад",
    sessMsg: "сообщ.",
    // Dataset
    datasetTitle: "Базы знаний",
    datasetSubtitle: "Выбери базу знаний, затем работай с документами и индексацией.",
    datasetCreate: "Создать базу знаний",
    datasetFiles: "файлов",
    datasetBack: "Все базы знаний",
    datasetAllBases: "Все базы знаний",
    datasetShow: "Показывать",
    datasetPrev: "Назад",
    datasetNext: "Далее",
    datasetPage: "Страница",
    datasetRename: "Переименовать",
    datasetDelete: "Удалить",
    datasetRenamePlaceholder: "Новое имя базы знаний",
    datasetTotalDocs: "Всего документов",
    datasetIndexed: "Индексировано",
    datasetPending: "Ожидает",
    datasetChunkSize: "Размер чанка",
    datasetAddDoc: "Добавить документ",
    datasetAddDocHint: "Загрузка документа в выбранную базу знаний.",
    datasetFile: "Файл",
    datasetSourceName: "Название источника",
    datasetSourcePlaceholder: "Например: ГОСТ 17375",
    datasetTags: "Теги",
    datasetUpload: "Добавить файл",
    datasetUploading: "Загрузка...",
    datasetRecentJobs: "Последние задачи",
    datasetRecentJobsHint: "Последние операции по этой базе знаний.",
    datasetNoJobs: "Задач пока нет.",
    datasetDocuments: "Документы",
    datasetDocumentsHint: "Нажми на документ, чтобы открыть чанки и ключевые слова.",
    datasetNoDocuments: "В этой базе знаний пока нет документов.",
    datasetIndexing: "Индексировать",
    datasetIndexInProgress: "В процессе...",
    datasetDeleteDoc: "Удалить",
    datasetKeywordsAfterIndex: "Ключевые слова появятся после индексации.",
    datasetDetailHint: "Документы внутри базы знаний.",
    datasetNotFound: "База знаний не найдена.",
    datasetDocumentNotFound: "Документ не найден в выбранной базе знаний.",
    datasetChunks: "Чанки",
    datasetChunksHint: "Нажми на чанк, чтобы открыть полный текст и ключевые слова.",
    datasetChunkSearch: "Поиск по чанкам и ключевым словам",
    datasetLoadingChunks: "Загрузка чанков...",
    datasetNoChunks: "Нет чанков для отображения.",
    datasetStatus: "Статус",
    datasetSource: "Источник",
    datasetChunkKeywords: "Ключевых слов на чанк",
    datasetKBSettings: "Настройки базы знаний",
    datasetKBSettingsHint: "Параметры, влияющие на индексацию.",
    datasetPreset: "Пресет",
    datasetChunkSizeLabel: "Размер чанка",
    datasetOverlap: "Перекрытие",
    datasetKeywordsPerChunk: "Ключевых слов на чанк",
    datasetReindex: "Переиндексировать всё",
    datasetReindexing: "Переиндексация...",
    datasetSaveSettings: "Сохранить",
    datasetSaving: "Сохранение...",
    datasetCreateTitle: "Создать базу знаний",
    datasetNameLabel: "Название",
    datasetNamePlaceholder: "Например: СДТ Отводы",
    datasetCancel: "Отмена",
    datasetCreating: "Создание...",
    datasetDeleteConfirm: "Удалить базу знаний",
    datasetPage404: "Страница не найдена",
    datasetTokens: "токенов",
    datasetKwChunk: "кл.сл./чанк",
    datasetDelimiters: "Разделители (через запятую)",
    datasetDelimitersPlaceholder: "Например: ---, ===",
    datasetUploadDocs: "Загрузить документы",
    datasetDropFiles: "Перетащите файлы сюда или нажмите для выбора",
    datasetUploadAll: "Загрузить",
  },

  en: {
    // Search
    title: "Paragraph Search",
    subtitle: "Semantic document search with fast preview of relevant snippets",
    queryPlaceholder: "Enter query",
    topKLabel: "Results",
    topKHint: "Number of results (1-50)",
    searchButton: "Search",
    loading: "Searching...",
    empty: "No results found",
    found: "Visible results",
    relevance: "Relevance",
    rawScore: "Raw score",
    knowledgeBase: "Knowledge base",
    content: "Content",
    keywords: "Keywords",
    noContent: "No content",
    noKeywords: "No keywords",
    errorPrefix: "Error",
    unexpectedError: "Unexpected error",
    sortLabel: "Sort",
    filterLabel: "Filter by keywords",
    clearFilters: "Clear",
    sortRelevanceDesc: "Most relevant first",
    sortRelevanceAsc: "Least relevant first",
    sortContentLengthDesc: "Longest snippets first",
    sortContentLengthAsc: "Shortest snippets first",
    copyContent: "Copy content",
    copyKeywords: "Copy keywords",
    copied: "Copied",
    themeLabel: "Theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeSystem: "System",
    // App
    ragWorkspace: "RAG workspace",
    // Chat
    chatSessions: "Sessions",
    chatDialogues: "Conversations",
    chatNewSession: "New session",
    chatNoSessions: "No sessions. Create one.",
    chatConversation: "Conversation",
    chatSelectSession: "Select a session",
    chatClear: "Clear",
    chatClearConfirm: "Delete conversation?",
    chatClearYes: "Yes",
    chatClearCancel: "Cancel",
    chatAllKBs: "All KBs",
    chatSelectKBs: "Select knowledge bases",
    chatEmptyTitle: "Start a conversation",
    chatEmptyHint: "Ask a question about your documents.",
    chatSuggestion1: "What is RAG?",
    chatSuggestion2: "What documents are loaded?",
    chatSuggestion3: "Give a brief summary",
    chatYou: "You",
    chatAssistant: "Assistant",
    chatSources: "Sources",
    chatPlaceholder: "Ask a question about your documents...",
    chatParams: "Settings",
    chatKBs: "Knowledge bases",
    chatSend: "Send",
    chatSending: "Sending...",
    chatThinking: "Thinking...",
    chatTyping: "Typing...",
    kbModalTitle: "Knowledge bases",
    kbModalHintAll: "Searching across all knowledge bases.",
    kbModalHintSelected: "{n} of {total} selected.",
    kbModalEmpty: "No knowledge bases found",
    kbModalReset: "Reset",
    kbModalApply: "Apply",
    kbDoc: "doc",
    msgSessionMissing: "Please select or create a session first",
    msgMessageRequired: "Please enter a message",
    justNow: "just now",
    minAgo: "min ago",
    hoursAgo: "h ago",
    sessMsg: "msg",
    // Dataset
    datasetTitle: "Knowledge bases",
    datasetSubtitle: "Select a knowledge base, then manage documents and indexing.",
    datasetCreate: "Create knowledge base",
    datasetFiles: "files",
    datasetBack: "All knowledge bases",
    datasetAllBases: "All knowledge bases",
    datasetShow: "Show",
    datasetPrev: "Previous",
    datasetNext: "Next",
    datasetPage: "Page",
    datasetRename: "Rename",
    datasetDelete: "Delete",
    datasetRenamePlaceholder: "New knowledge base name",
    datasetTotalDocs: "Total documents",
    datasetIndexed: "Indexed",
    datasetPending: "Pending",
    datasetChunkSize: "Chunk size",
    datasetAddDoc: "Add document",
    datasetAddDocHint: "Upload a document to the selected knowledge base.",
    datasetFile: "File",
    datasetSourceName: "Source name",
    datasetSourcePlaceholder: "e.g. GOST 17375",
    datasetTags: "Tags",
    datasetUpload: "Add file",
    datasetUploading: "Uploading...",
    datasetRecentJobs: "Recent jobs",
    datasetRecentJobsHint: "Latest operations for this knowledge base.",
    datasetNoJobs: "No jobs yet.",
    datasetDocuments: "Documents",
    datasetDocumentsHint: "Click a document to view chunks and auto-generated keywords.",
    datasetNoDocuments: "No documents in this knowledge base yet.",
    datasetIndexing: "Index",
    datasetIndexInProgress: "In progress...",
    datasetDeleteDoc: "Delete",
    datasetKeywordsAfterIndex: "Keywords will appear after indexing.",
    datasetDetailHint: "Documents in this knowledge base.",
    datasetNotFound: "Knowledge base not found.",
    datasetDocumentNotFound: "Document not found in the selected knowledge base.",
    datasetChunks: "Chunks",
    datasetChunksHint: "Click a chunk to view full text and keywords.",
    datasetChunkSearch: "Search chunks and keywords",
    datasetLoadingChunks: "Loading chunks...",
    datasetNoChunks: "No chunks to display.",
    datasetStatus: "Status",
    datasetSource: "Source",
    datasetChunkKeywords: "Keywords per chunk",
    datasetKBSettings: "Knowledge base settings",
    datasetKBSettingsHint: "Parameters that affect indexing.",
    datasetPreset: "Preset",
    datasetChunkSizeLabel: "Chunk size",
    datasetOverlap: "Overlap",
    datasetKeywordsPerChunk: "Keywords per chunk",
    datasetReindex: "Reindex all",
    datasetReindexing: "Reindexing...",
    datasetSaveSettings: "Save settings",
    datasetSaving: "Saving...",
    datasetCreateTitle: "Create knowledge base",
    datasetNameLabel: "Name",
    datasetNamePlaceholder: "e.g. SDT Bends",
    datasetCancel: "Cancel",
    datasetCreating: "Creating...",
    datasetDeleteConfirm: "Delete knowledge base",
    datasetPage404: "Page not found",
    datasetTokens: "tokens",
    datasetKwChunk: "kw/chunk",
    datasetDelimiters: "Delimiters (comma-separated)",
    datasetDelimitersPlaceholder: "e.g.: ---, ===",
    datasetUploadDocs: "Upload documents",
    datasetDropFiles: "Drop files here or click to browse",
    datasetUploadAll: "Upload",
  }
};

export const STORAGE_LANG_KEY = "language";

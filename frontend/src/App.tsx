import { useState } from "react";

import { ChatPage } from "./components/ChatPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";

type TabKey = "search" | "documents" | "chat";

const tabMeta: Record<TabKey, { label: string; kicker: string; description: string }> = {
  search: {
    label: "Search",
    kicker: "Retrieval",
    description: "Семантический поиск, source preview и аналитический режим."
  },
  documents: {
    label: "Dataset",
    kicker: "Knowledge Ops",
    description: "Базы знаний, документы, индексация и статусы в одном workspace."
  },
  chat: {
    label: "Chat",
    kicker: "Copilot",
    description: "Диалоги по выбранным базам знаний с переходом к источникам."
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("search");
  const currentTab = tabMeta[activeTab];

  return (
    <div className="page-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="page app-page">
        <header className="app-header app-shell">
          <div className="app-brand-block">
            <span className="app-kicker">RAG Control Center</span>
            <h1>RAG Workspace</h1>
            <p>Поиск, базы знаний и чат в одном интерфейсе.</p>
          </div>
          <div className="app-shell-side">
            <nav className="tab-nav app-segmented-nav" aria-label="Навигация разделов">
              {(Object.keys(tabMeta) as TabKey[]).map((tabKey) => {
                const item = tabMeta[tabKey];
                return (
                  <button
                    key={tabKey}
                    type="button"
                    className={`tab-btn app-nav-pill ${activeTab === tabKey ? "active" : ""}`}
                    onClick={() => setActiveTab(tabKey)}
                  >
                    <span>{item.label}</span>
                    <small>{item.kicker}</small>
                  </button>
                );
              })}
            </nav>
            <div className="app-status-rail">
              <article className="app-status-card active">
                <span>Mode</span>
                <strong>{currentTab.label}</strong>
              </article>
              <article className="app-status-card">
                <span>Focus</span>
                <strong>{currentTab.kicker}</strong>
              </article>
              <article className="app-status-card app-status-wide">
                <span>Context</span>
                <strong>{currentTab.description}</strong>
              </article>
            </div>
          </div>
        </header>

        {activeTab === "search" && <SearchPage embedded />}
        {activeTab === "documents" && <DocumentsPage />}
        {activeTab === "chat" && <ChatPage />}
      </main>
    </div>
  );
}

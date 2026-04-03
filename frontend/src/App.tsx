import { useState } from "react";

import { ChatPage } from "./components/ChatPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";

type TabKey = "search" | "documents" | "chat";

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>("search");

  return (
    <div className="page-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <main className="page app-page">
        <header className="app-header">
          <div>
            <h1>RAG Workspace</h1>
            <p>Поиск, документы и чат в одном интерфейсе.</p>
          </div>
          <nav className="tab-nav" aria-label="Навигация разделов">
            <button
              type="button"
              className={`tab-btn ${activeTab === "search" ? "active" : ""}`}
              onClick={() => setActiveTab("search")}
            >
              Search
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "documents" ? "active" : ""}`}
              onClick={() => setActiveTab("documents")}
            >
              Documents
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => setActiveTab("chat")}
            >
              Chat
            </button>
          </nav>
        </header>

        {activeTab === "search" && <SearchPage embedded />}
        {activeTab === "documents" && <DocumentsPage />}
        {activeTab === "chat" && <ChatPage />}
      </main>
    </div>
  );
}

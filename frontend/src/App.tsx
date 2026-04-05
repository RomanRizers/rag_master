import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { ChatPage } from "./components/ChatPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";

type AppSection = {
  label: string;
  title: string;
  subtitle: string;
  href: string;
};

const SECTIONS: AppSection[] = [
  {
    label: "Dataset",
    title: "Dataset",
    subtitle: "Сетка баз знаний и отдельные рабочие экраны для каждой базы.",
    href: "/dataset"
  },
  {
    label: "Chat",
    title: "Chat",
    subtitle: "Диалог по выбранным документам и базам знаний.",
    href: "/chat"
  },
  {
    label: "Search",
    title: "Search",
    subtitle: "Быстрый поиск по фрагментам и источникам.",
    href: "/search"
  }
];

function resolveSection(pathname: string): AppSection {
  if (pathname.startsWith("/chat")) {
    return SECTIONS[1];
  }
  if (pathname.startsWith("/search")) {
    return SECTIONS[2];
  }
  return SECTIONS[0];
}

function AppShell() {
  const location = useLocation();
  const active = resolveSection(location.pathname);

  return (
    <div className="page-shell">
      <main className="page app-page">
        <header className="app-header">
          <div className="app-header-copy">
            <span className="section-kicker">RAG workspace</span>
            <h1>{active.title}</h1>
            <p>{active.subtitle}</p>
          </div>
          <nav className="tab-nav" aria-label="Навигация разделов">
            {SECTIONS.map((section) => (
              <NavLink
                key={section.href}
                to={section.href}
                className={({ isActive }) => `tab-btn ${isActive ? "active" : ""}`}
              >
                {section.label}
              </NavLink>
            ))}
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<Navigate to="/dataset" replace />} />
          <Route path="/dataset" element={<DocumentsPage />} />
          <Route path="/dataset/:datasetName" element={<DocumentsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/search" element={<SearchPage embedded />} />
          <Route path="*" element={<Navigate to="/dataset" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return <AppShell />;
}

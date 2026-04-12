import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { ChatPage } from "./components/ChatPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";
import { STORAGE_LANG_KEY, type Language } from "./i18n";
import { getSystemPrefersDark, parseThemeMode, resolveTheme, STORAGE_THEME_KEY, type ThemeMode } from "./theme";

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

function getInitialLanguage(): Language {
  const saved = localStorage.getItem(STORAGE_LANG_KEY);
  return saved === "en" ? "en" : "ru";
}

function AppShell() {
  const location = useLocation();
  const active = resolveSection(location.pathname);
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const [themeMode, setThemeMode] = useState<ThemeMode>(() =>
    parseThemeMode(localStorage.getItem(STORAGE_THEME_KEY))
  );

  useEffect(() => {
    function applyTheme() {
      const nextTheme = resolveTheme(themeMode, getSystemPrefersDark());
      document.documentElement.setAttribute("data-theme", nextTheme);
    }

    applyTheme();

    if (themeMode !== "system") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", applyTheme);
      return () => mediaQuery.removeEventListener("change", applyTheme);
    }
    mediaQuery.addListener(applyTheme);
    return () => mediaQuery.removeListener(applyTheme);
  }, [themeMode]);

  function switchLanguage(nextLanguage: Language) {
    setLanguage(nextLanguage);
    localStorage.setItem(STORAGE_LANG_KEY, nextLanguage);
  }

  function switchTheme(nextTheme: ThemeMode) {
    setThemeMode(nextTheme);
    localStorage.setItem(STORAGE_THEME_KEY, nextTheme);
  }

  return (
    <div className="page-shell">
      <main className="page app-page">
        <header className="app-header">
          <div className="app-header-main">
            <div className="app-header-copy">
              <span className="section-kicker">RAG workspace</span>
              <h1>{active.title}</h1>
              <p>{active.subtitle}</p>
            </div>
            <div className="app-header-controls">
              <div className="lang-switch" role="group" aria-label="Language switch">
                <button
                  type="button"
                  className={language === "ru" ? "lang-btn active" : "lang-btn"}
                  onClick={() => switchLanguage("ru")}
                >
                  RU
                </button>
                <button
                  type="button"
                  className={language === "en" ? "lang-btn active" : "lang-btn"}
                  onClick={() => switchLanguage("en")}
                >
                  EN
                </button>
              </div>
              <label className="theme-switch">
                <span>Theme</span>
                <select value={themeMode} onChange={(event) => switchTheme(event.target.value as ThemeMode)}>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </label>
            </div>
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
          <Route path="/dataset/:datasetName/documents/:documentId" element={<DocumentsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/search" element={<SearchPage embedded language={language} />} />
          <Route path="*" element={<Navigate to="/dataset" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return <AppShell />;
}

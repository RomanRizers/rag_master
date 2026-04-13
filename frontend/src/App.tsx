import { useEffect, useRef, useState } from "react";
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
  icon: React.ReactNode;
};

const SECTIONS: AppSection[] = [
  {
    label: "Dataset",
    title: "Dataset",
    subtitle: "Сетка баз знаний и отдельные рабочие экраны для каждой базы.",
    href: "/dataset",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <ellipse cx="12" cy="6" rx="8" ry="3" stroke="currentColor" strokeWidth="1.8" />
        <path d="M4 6v6c0 1.66 3.58 3 8 3s8-1.34 8-3V6" stroke="currentColor" strokeWidth="1.8" />
        <path d="M4 12v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6" stroke="currentColor" strokeWidth="1.8" />
      </svg>
    )
  },
  {
    label: "Chat",
    title: "Chat",
    subtitle: "Диалог по выбранным документам и базам знаний.",
    href: "/chat",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    )
  },
  {
    label: "Search",
    title: "Search",
    subtitle: "Быстрый поиск по фрагментам и источникам.",
    href: "/search",
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
        <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
];

function resolveSection(pathname: string): AppSection {
  if (pathname.startsWith("/chat")) return SECTIONS[1];
  if (pathname.startsWith("/search")) return SECTIONS[2];
  return SECTIONS[0];
}

function getInitialLanguage(): Language {
  const saved = localStorage.getItem(STORAGE_LANG_KEY);
  return saved === "en" ? "en" : "ru";
}

function TabNav() {
  const location = useLocation();
  const navRef = useRef<HTMLElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });

  useEffect(() => {
    const nav = navRef.current;
    if (!nav) return;
    const active = nav.querySelector<HTMLElement>(".tab-btn.active");
    if (active) {
      setIndicatorStyle({ left: active.offsetLeft, width: active.offsetWidth });
    }
  }, [location.pathname]);

  return (
    <nav ref={navRef} className="tab-nav" aria-label="Навигация разделов">
      <span
        className="tab-indicator"
        style={{ transform: `translateX(${indicatorStyle.left}px)`, width: indicatorStyle.width }}
      />
      {SECTIONS.map((section) => (
        <NavLink
          key={section.href}
          to={section.href}
          className={({ isActive }) => `tab-btn ${isActive ? "active" : ""}`}
        >
          {section.icon}
          {section.label}
        </NavLink>
      ))}
    </nav>
  );
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
    if (themeMode !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    if (typeof mq.addEventListener === "function") {
      mq.addEventListener("change", applyTheme);
      return () => mq.removeEventListener("change", applyTheme);
    }
    mq.addListener(applyTheme);
    return () => mq.removeListener(applyTheme);
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
              <div className="app-logo">
                <span className="app-logo-mark" aria-hidden="true">R</span>
                <div>
                  <span className="section-kicker">RAG workspace</span>
                  <h1>{active.title}</h1>
                </div>
              </div>
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
                <select value={themeMode} onChange={(e) => switchTheme(e.target.value as ThemeMode)}>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </label>
            </div>
          </div>
          <TabNav />
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

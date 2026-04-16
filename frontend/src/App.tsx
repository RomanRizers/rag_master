import { useEffect, useRef, useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";

import { ChatPage } from "./components/ChatPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";
import { copy, STORAGE_LANG_KEY, type Language } from "./i18n";
import { LangContext } from "./LangContext";
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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!settingsOpen) return;
    function onPointerDown(e: PointerEvent) {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [settingsOpen]);

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

  const t = copy[language];

  return (
    <LangContext.Provider value={language}>
      <div className="page-shell">
        <main className="page app-page">
          <header className="app-header">
            <div className="app-logo">
              <span className="app-logo-mark" aria-hidden="true">R</span>
              <div>
                <span className="section-kicker">{t.ragWorkspace}</span>
                <h1>{active.title}</h1>
              </div>
            </div>

            <div className="app-header-right">
              <TabNav />
              <div className="settings-popover-wrap" ref={settingsRef}>
                <button
                  type="button"
                  className={`settings-gear-btn${settingsOpen ? " active" : ""}`}
                  aria-label="Настройки"
                  onClick={() => setSettingsOpen((v) => !v)}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
                      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
                    />
                    <path
                      d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
                      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
                    />
                  </svg>
                </button>

                {settingsOpen && (
                  <div className="settings-popover">
                    <div className="settings-popover-row">
                      <span className="settings-popover-label">{t.themeLabel}</span>
                      <div className="lang-switch" role="group">
                        {(["light", "dark", "system"] as const).map((mode) => (
                          <button
                            key={mode}
                            type="button"
                            className={themeMode === mode ? "lang-btn active" : "lang-btn"}
                            onClick={() => switchTheme(mode)}
                          >
                            {mode === "light" ? t.themeLight : mode === "dark" ? t.themeDark : t.themeSystem}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="settings-popover-row">
                      <span className="settings-popover-label">{t.themeLabel === "Тема" ? "Язык" : "Language"}</span>
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
                    </div>
                  </div>
                )}
              </div>
            </div>
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
    </LangContext.Provider>
  );
}

export default function App() {
  return <AppShell />;
}

import { createContext, useContext } from "react";
import { copy, type Copy, type Language } from "./i18n";

export const LangContext = createContext<Language>("ru");

export function useLang(): Copy {
  const lang = useContext(LangContext);
  return copy[lang];
}

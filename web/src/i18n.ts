import { useEffect, useMemo, useState } from "react";
import { getLanguages, type LanguageOption } from "./api";

type Dictionary = Record<string, string>;
export type TFunction = (key: string, values?: Record<string, string | number>) => string;

const DEFAULT_LANGUAGE = "en";
const STORAGE_KEY = "sessionview.language";

export function useI18n() {
  const [languages, setLanguages] = useState<LanguageOption[]>([
    { code: "en", name: "English", native_name: "English" },
    { code: "zh", name: "Chinese", native_name: "中文" }
  ]);
  const [language, setLanguage] = useState(() => initialLanguage());
  const [dictionary, setDictionary] = useState<Dictionary>({});

  useEffect(() => {
    getLanguages()
      .then((items) => {
        setLanguages(items);
        if (items.length > 0 && !items.some((item) => item.code === language)) {
          const fallback = pickLanguage(items);
          setLanguage(fallback);
          localStorage.setItem(STORAGE_KEY, fallback);
        }
      })
      .catch(() => {
        setLanguages([
          { code: "en", name: "English", native_name: "English" },
          { code: "zh", name: "Chinese", native_name: "中文" }
        ]);
      });
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, language);
    loadDictionary(language)
      .then(setDictionary)
      .catch(async () => {
        if (language !== DEFAULT_LANGUAGE) {
          setDictionary(await loadDictionary(DEFAULT_LANGUAGE));
        }
      });
  }, [language]);

  const t = useMemo<TFunction>(() => {
    return (key, values) => format(dictionary[key] ?? key, values);
  }, [dictionary]);

  return { language, languages, setLanguage, t };
}

async function loadDictionary(language: string): Promise<Dictionary> {
  const response = await fetch(`/locales/${encodeURIComponent(language)}.csv`);
  if (!response.ok) {
    throw new Error(`Locale not found: ${language}`);
  }
  return parseCsv(await response.text());
}

function initialLanguage() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) return stored;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh" : DEFAULT_LANGUAGE;
}

function pickLanguage(languages: LanguageOption[]) {
  const browserLanguage = navigator.language.toLowerCase();
  const browserMatch = languages.find((item) => browserLanguage.startsWith(item.code.toLowerCase()));
  return browserMatch?.code ?? languages.find((item) => item.code === DEFAULT_LANGUAGE)?.code ?? languages[0].code;
}

function parseCsv(text: string): Dictionary {
  const rows = parseRows(text);
  const [header, ...body] = rows;
  const keyIndex = header?.indexOf("key") ?? -1;
  const valueIndex = header?.indexOf("value") ?? -1;
  if (keyIndex < 0 || valueIndex < 0) {
    throw new Error("Locale CSV must contain key and value columns");
  }
  return body.reduce<Dictionary>((acc, row) => {
    const key = row[keyIndex]?.trim();
    if (key) {
      acc[key] = row[valueIndex] ?? "";
    }
    return acc;
  }, {});
}

function parseRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (quoted) {
      if (char === '"' && next === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") {
      cell += char;
    }
  }
  row.push(cell);
  if (row.some((value) => value.length > 0)) {
    rows.push(row);
  }
  return rows;
}

function format(template: string, values?: Record<string, string | number>) {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));
}

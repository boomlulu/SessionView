import { RefreshCw, Search } from "lucide-react";
import type { LanguageOption } from "../api";
import { tailPath } from "../format";
import type { TFunction } from "../i18n";

type Props = {
  query: string;
  project: string;
  projects: string[];
  language: string;
  languages: LanguageOption[];
  isScanning: boolean;
  t: TFunction;
  onQueryChange: (value: string) => void;
  onProjectChange: (value: string) => void;
  onLanguageChange: (value: string) => void;
  onScan: () => void;
};

export function SearchBar({
  query,
  project,
  projects,
  language,
  languages,
  isScanning,
  t,
  onQueryChange,
  onProjectChange,
  onLanguageChange,
  onScan
}: Props) {
  return (
    <div className="toolbar">
      <label className="searchBox">
        <Search size={18} aria-hidden="true" />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={t("search.placeholder")}
          aria-label={t("search.aria")}
        />
      </label>
      <select value={project} onChange={(event) => onProjectChange(event.target.value)} aria-label={t("project.aria")}>
        <option value="">{t("project.all")}</option>
        {projects.map((item) => (
          <option key={item} value={item}>
            {tailPath(item)}
          </option>
        ))}
      </select>
      <select
        className="languageSelect"
        value={language}
        onChange={(event) => onLanguageChange(event.target.value)}
        aria-label={t("language.aria")}
      >
        {languages.map((item) => (
          <option key={item.code} value={item.code}>
            {item.native_name}
          </option>
        ))}
      </select>
      <button className="iconButton primary" onClick={onScan} disabled={isScanning} title={t("scan.title")}>
        <RefreshCw size={18} className={isScanning ? "spin" : ""} aria-hidden="true" />
        <span>{isScanning ? t("scan.scanning") : t("scan.button")}</span>
      </button>
    </div>
  );
}

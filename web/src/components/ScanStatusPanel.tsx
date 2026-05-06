import { CheckCircle2, FolderSearch, Loader2, XCircle } from "lucide-react";
import type { ScanStatus } from "../api";
import type { TFunction } from "../i18n";

type Props = {
  status: ScanStatus | null;
  t: TFunction;
};

export function ScanStatusPanel({ status, t }: Props) {
  if (!status) return null;
  const total = status.total_files;
  const scanned = status.scanned_files;
  const percent = total > 0 ? Math.min(100, Math.round((scanned / total) * 100)) : 0;
  const phaseLabel = t(`scan.phase.${status.phase}`);
  const Icon = status.phase === "failed" ? XCircle : status.running ? Loader2 : CheckCircle2;

  return (
    <section className="scanPanel" aria-label={t("scan.panelAria")}>
      <div className="scanPanelHeader">
        <div className="scanTitle">
          <Icon size={18} className={status.running ? "spin" : ""} aria-hidden="true" />
          <strong>{phaseLabel}</strong>
        </div>
        <span>{t("scan.progress", { scanned, total })}</span>
      </div>

      <div className="progressTrack">
        <div className="progressFill" style={{ width: `${percent}%` }} />
      </div>

      <div className="scanGrid">
        <div>
          <p className="scanLabel">{t("scan.roots")}</p>
          <ul className="rootList">
            {status.roots.map((root) => (
              <li key={root.path} className={root.exists ? "" : "missingRoot"}>
                <FolderSearch size={14} aria-hidden="true" />
                <span>{root.path}</span>
                <em>{root.exists ? t("scan.rootExists") : t("scan.rootMissing")}</em>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="scanLabel">{t("scan.currentFile")}</p>
          <p className="currentFile">{status.current_file || t("scan.noCurrentFile")}</p>
          <p className="scanCounts">
            {t("scan.counts", {
              indexed: status.indexed_sessions,
              warnings: status.warnings.length
            })}
          </p>
        </div>
      </div>

      {status.error && <p className="scanError">{status.error}</p>}
      {status.warnings.length > 0 && (
        <details className="warningList">
          <summary>{t("scan.warnings", { count: status.warnings.length })}</summary>
          <ul>
            {status.warnings.slice(-8).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

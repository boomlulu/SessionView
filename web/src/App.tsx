import { useEffect, useMemo, useState } from "react";
import { Database } from "lucide-react";
import {
  deleteScanRoot,
  getHealth,
  getProjects,
  getScanStatus,
  getSession,
  searchSessions,
  startScan,
  type Health,
  type ScanStatus,
  type SessionDetail,
  type SessionSummary
} from "./api";
import { ScanStatusPanel } from "./components/ScanStatusPanel";
import { SearchBar } from "./components/SearchBar";
import { SessionDetailView } from "./components/SessionDetail";
import { SessionList } from "./components/SessionList";
import { useI18n } from "./i18n";

export function App() {
  const { language, languages, setLanguage, t } = useI18n();
  const [health, setHealth] = useState<Health | null>(null);
  const [projects, setProjects] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [project, setProject] = useState("");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusKey, setStatusKey] = useState("app.ready");
  const [statusValues, setStatusValues] = useState<Record<string, string | number> | undefined>();
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    void refreshStatus();
  }, []);

  useEffect(() => {
    getScanStatus()
      .then((status) => {
        setScanStatus(status);
        setIsScanning(status.running);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!isScanning) return;
    const timer = window.setInterval(() => {
      void pollScanStatus();
    }, 600);
    return () => window.clearInterval(timer);
  }, [isScanning]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void runSearch();
    }, 180);
    return () => window.clearTimeout(timer);
  }, [query, project]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    getSession(selectedId)
      .then(setDetail)
      .catch((err) => setError(readableError(err)))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const indexLabel = useMemo(() => {
    if (!health) return t("app.indexUnknown");
    return t("app.indexedSessions", { count: health.session_count });
  }, [health, t]);
  const selectedSummary = sessions.find((item) => item.session_id === selectedId);
  const displayedDetail = detail
    ? {
        ...detail,
        snippet: selectedSummary?.snippet ?? detail.snippet
      }
    : null;

  async function refreshStatus() {
    try {
      const [healthPayload, projectPayload] = await Promise.all([getHealth(), getProjects()]);
      setHealth(healthPayload);
      setProjects(projectPayload);
      setStatusKey("app.ready");
      setStatusValues(undefined);
      await runSearch();
    } catch (err) {
      setError(readableError(err));
      setStatusKey("app.apiUnavailable");
      setStatusValues(undefined);
      setLoading(false);
    }
  }

  async function runSearch() {
    setLoading(true);
    setError(null);
    try {
      const result = await searchSessions(query, project);
      setSessions(result);
      if (result.length > 0 && !result.some((item) => item.session_id === selectedId)) {
        setSelectedId(result[0].session_id);
      }
      if (result.length === 0) {
        setSelectedId(null);
      }
    } catch (err) {
      setError(readableError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    await startScanForRoots(undefined, "app.scanning");
  }

  async function handleProjectChange(value: string) {
    setProject(value);
    if (!value) return;
    await startScanForRoots([value], "app.scanningProject");
  }

  async function startScanForRoots(roots: string[] | undefined, statusKey: string) {
    setIsScanning(true);
    setStatusKey(statusKey);
    setStatusValues(undefined);
    try {
      const status = await startScan(false, roots);
      setScanStatus(status);
      if (!status.running) {
        await finishScan(status);
      }
    } catch (err) {
      setError(readableError(err));
      setStatusKey("app.scanFailed");
      setStatusValues(undefined);
      setIsScanning(false);
    }
  }

  async function pollScanStatus() {
    try {
      const status = await getScanStatus();
      setScanStatus(status);
      if (!status.running) {
        await finishScan(status);
      }
    } catch (err) {
      setError(readableError(err));
      setStatusKey("app.scanFailed");
      setStatusValues(undefined);
      setIsScanning(false);
    }
  }

  async function finishScan(status: ScanStatus) {
    setIsScanning(false);
    if (status.phase === "failed") {
      setStatusKey("app.scanFailed");
      setStatusValues(undefined);
      return;
    }
    await refreshStatus();
    setStatusKey("app.scanComplete");
    setStatusValues({ indexed: status.indexed_sessions, files: status.scanned_files });
  }

  async function handleDeleteScanRoot(path: string) {
    const roots = await deleteScanRoot(path);
    setScanStatus((current) => (current ? { ...current, roots } : current));
  }

  async function handleCopy(command: string) {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <main className="appShell">
      <header className="topbar">
        <div className="brand">
          <Database size={22} aria-hidden="true" />
          <div>
            <strong>{t("brand.name")}</strong>
            <span>{indexLabel}</span>
          </div>
        </div>
        <SearchBar
          query={query}
          project={project}
          projects={projects}
          language={language}
          languages={languages}
          isScanning={isScanning}
          t={t}
          onQueryChange={setQuery}
          onProjectChange={handleProjectChange}
          onLanguageChange={setLanguage}
          onScan={handleScan}
        />
      </header>
      <div className="statusBar">{t(statusKey, statusValues)}</div>
      <ScanStatusPanel
        status={scanStatus}
        dbPath={health?.db_path ?? null}
        disabled={isScanning}
        t={t}
        onDeleteRoot={handleDeleteScanRoot}
      />
      <div className="contentGrid">
        <SessionList
          sessions={sessions}
          selectedId={selectedId}
          loading={loading}
          error={error}
          t={t}
          onSelect={setSelectedId}
        />
        <SessionDetailView detail={displayedDetail} loading={detailLoading} copied={copied} t={t} onCopy={handleCopy} />
      </div>
    </main>
  );
}

function readableError(err: unknown) {
  if (err instanceof Error) return err.message;
  return String(err);
}

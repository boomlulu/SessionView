import { useEffect, useMemo, useState } from "react";
import { Database } from "lucide-react";
import { getHealth, getProjects, getSession, scan, searchSessions, type Health, type SessionDetail, type SessionSummary } from "./api";
import { SearchBar } from "./components/SearchBar";
import { SessionDetailView } from "./components/SessionDetail";
import { SessionList } from "./components/SessionList";

export function App() {
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
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("Ready");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    void refreshStatus();
  }, []);

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
    if (!health) return "Index unknown";
    return `${health.session_count} indexed sessions`;
  }, [health]);
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
      setStatus("Ready");
      await runSearch();
    } catch (err) {
      setError(readableError(err));
      setStatus("API unavailable");
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
    setIsScanning(true);
    setStatus("Scanning transcripts");
    try {
      const report = await scan(false);
      setStatus(`Indexed ${report.indexed_sessions} sessions from ${report.scanned_files} files`);
      await refreshStatus();
    } catch (err) {
      setError(readableError(err));
      setStatus("Scan failed");
    } finally {
      setIsScanning(false);
    }
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
            <strong>SessionView</strong>
            <span>{indexLabel}</span>
          </div>
        </div>
        <SearchBar
          query={query}
          project={project}
          projects={projects}
          isScanning={isScanning}
          onQueryChange={setQuery}
          onProjectChange={setProject}
          onScan={handleScan}
        />
      </header>
      <div className="statusBar">{status}</div>
      <div className="contentGrid">
        <SessionList
          sessions={sessions}
          selectedId={selectedId}
          loading={loading}
          error={error}
          onSelect={setSelectedId}
        />
        <SessionDetailView detail={displayedDetail} loading={detailLoading} copied={copied} onCopy={handleCopy} />
      </div>
    </main>
  );
}

function readableError(err: unknown) {
  if (err instanceof Error) return err.message;
  return String(err);
}

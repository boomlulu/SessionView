import type { SessionSummary } from "../api";
import { highlightHtml, shortDate } from "../format";

type Props = {
  sessions: SessionSummary[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (sessionId: string) => void;
};

export function SessionList({ sessions, selectedId, loading, error, onSelect }: Props) {
  if (loading) {
    return <div className="state">Loading sessions...</div>;
  }
  if (error) {
    return <div className="state error">{error}</div>;
  }
  if (sessions.length === 0) {
    return <div className="state">No sessions yet. Scan transcripts or try another keyword.</div>;
  }
  return (
    <div className="sessionList" aria-label="Session results">
      {sessions.map((session) => (
        <button
          key={session.session_id}
          className={`sessionItem ${selectedId === session.session_id ? "selected" : ""}`}
          onClick={() => onSelect(session.session_id)}
        >
          <span className="itemTop">
            <span className="projectName">{session.project_path || "unknown project"}</span>
            <span className="time">{shortDate(session.updated_at || session.created_at)}</span>
          </span>
          <span className="prompt">{session.first_user_text || "No user prompt found"}</span>
          {session.snippet && (
            <span className="snippet" dangerouslySetInnerHTML={{ __html: highlightHtml(session.snippet) }} />
          )}
          <span className="meta">{session.message_count} messages</span>
        </button>
      ))}
    </div>
  );
}

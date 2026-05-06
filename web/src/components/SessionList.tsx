import type { SessionSummary } from "../api";
import { highlightHtml, shortDate } from "../format";
import type { TFunction } from "../i18n";

type Props = {
  sessions: SessionSummary[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  t: TFunction;
  onSelect: (sessionId: string) => void;
};

export function SessionList({ sessions, selectedId, loading, error, t, onSelect }: Props) {
  if (loading) {
    return <div className="state">{t("status.loadingSessions")}</div>;
  }
  if (error) {
    return <div className="state error">{error}</div>;
  }
  if (sessions.length === 0) {
    return <div className="state">{t("status.noSessions")}</div>;
  }
  return (
    <div className="sessionList" aria-label={t("list.aria")}>
      {sessions.map((session) => (
        <button
          key={session.session_id}
          className={`sessionItem ${selectedId === session.session_id ? "selected" : ""}`}
          onClick={() => onSelect(session.session_id)}
        >
          <span className="itemTop">
            <span className="projectName">{session.project_path || t("list.unknownProject")}</span>
            <span className="time">{shortDate(session.updated_at || session.created_at)}</span>
          </span>
          <span className="prompt">{session.first_user_text || t("list.noPrompt")}</span>
          {session.snippet && (
            <span className="snippet" dangerouslySetInnerHTML={{ __html: highlightHtml(session.snippet) }} />
          )}
          <span className="meta">{t("list.messages", { count: session.message_count })}</span>
        </button>
      ))}
    </div>
  );
}

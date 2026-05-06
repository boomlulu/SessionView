import { Clipboard, FileText } from "lucide-react";
import type { SessionDetail } from "../api";
import { highlightHtml, shortDate } from "../format";

type Props = {
  detail: SessionDetail | null;
  loading: boolean;
  copied: boolean;
  onCopy: (command: string) => void;
};

export function SessionDetailView({ detail, loading, copied, onCopy }: Props) {
  if (loading) {
    return <section className="detailPanel state">Loading detail...</section>;
  }
  if (!detail) {
    return (
      <section className="detailPanel emptyDetail">
        <FileText size={28} aria-hidden="true" />
        <p>Select a session to inspect its transcript path, preview, and resume command.</p>
      </section>
    );
  }
  return (
    <section className="detailPanel">
      <div className="detailHeader">
        <div>
          <p className="eyebrow">{detail.project_path || "unknown project"}</p>
          <h1>{detail.first_user_text || detail.session_id}</h1>
        </div>
        <span className="count">{detail.message_count} messages</span>
      </div>

      <div className="commandRow">
        <code>{detail.resume_command}</code>
        <button className="iconButton" onClick={() => onCopy(detail.resume_command)} title="Copy resume command">
          <Clipboard size={17} aria-hidden="true" />
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>

      <dl className="facts">
        <div>
          <dt>Updated</dt>
          <dd>{shortDate(detail.updated_at || detail.created_at) || "unknown"}</dd>
        </div>
        <div>
          <dt>Transcript</dt>
          <dd>{detail.transcript_path}</dd>
        </div>
        <div>
          <dt>Session ID</dt>
          <dd>{detail.session_id}</dd>
        </div>
      </dl>

      {detail.snippet && (
        <div className="snippetBlock">
          <h2>Match</h2>
          <p dangerouslySetInnerHTML={{ __html: highlightHtml(detail.snippet) }} />
        </div>
      )}

      <div className="messages">
        <h2>Preview</h2>
        {detail.messages.slice(0, 12).map((message) => (
          <article key={message.id} className="message">
            <div className="messageMeta">
              <span>{message.role}</span>
              <span>{shortDate(message.timestamp)}</span>
            </div>
            <p>{message.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

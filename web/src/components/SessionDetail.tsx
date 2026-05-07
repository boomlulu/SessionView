import { Clipboard, FileText } from "lucide-react";
import type { SessionDetail } from "../api";
import { highlightHtml, shortDate, tailPath } from "../format";
import type { TFunction } from "../i18n";
import { MarkdownPreview } from "./MarkdownPreview";

type Props = {
  detail: SessionDetail | null;
  loading: boolean;
  copied: boolean;
  t: TFunction;
  onCopy: (command: string) => void;
};

export function SessionDetailView({ detail, loading, copied, t, onCopy }: Props) {
  if (loading) {
    return <section className="detailPanel state">{t("detail.loading")}</section>;
  }
  if (!detail) {
    return (
      <section className="detailPanel emptyDetail">
        <FileText size={28} aria-hidden="true" />
        <p>{t("detail.empty")}</p>
      </section>
    );
  }
  return (
    <section className="detailPanel">
      <div className="detailHeader">
        <div>
          <p className="eyebrow" title={detail.project_path || undefined}>
            {tailPath(detail.project_path) || t("list.unknownProject")}
          </p>
          <h1>{detail.first_user_text || detail.session_id}</h1>
        </div>
        <span className="count">{t("list.messages", { count: detail.message_count })}</span>
      </div>

      <div className="commandRow">
        <code>{detail.resume_command}</code>
        <button className="iconButton" onClick={() => onCopy(detail.resume_command)} title={t("detail.copyTitle")}>
          <Clipboard size={17} aria-hidden="true" />
          <span>{copied ? t("detail.copied") : t("detail.copy")}</span>
        </button>
      </div>

      <dl className="facts">
        <div>
          <dt>{t("detail.updated")}</dt>
          <dd>{shortDate(detail.updated_at || detail.created_at) || t("detail.unknown")}</dd>
        </div>
        <div>
          <dt>{t("detail.transcript")}</dt>
          <dd>{detail.transcript_path}</dd>
        </div>
        <div>
          <dt>{t("detail.sessionId")}</dt>
          <dd>{detail.session_id}</dd>
        </div>
      </dl>

      {detail.snippet && (
        <div className="snippetBlock">
          <h2>{t("detail.match")}</h2>
          <p dangerouslySetInnerHTML={{ __html: highlightHtml(detail.snippet) }} />
        </div>
      )}

      <div className="messages">
        <h2>{t("detail.preview")}</h2>
        {detail.messages.slice(0, 12).map((message) => (
          <article key={message.id} className="message">
            <div className="messageMeta">
              <span>{message.role}</span>
              <span>{shortDate(message.timestamp)}</span>
            </div>
            <MarkdownPreview>{message.text}</MarkdownPreview>
          </article>
        ))}
      </div>
    </section>
  );
}

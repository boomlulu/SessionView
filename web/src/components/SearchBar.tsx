import { RefreshCw, Search } from "lucide-react";

type Props = {
  query: string;
  project: string;
  projects: string[];
  isScanning: boolean;
  onQueryChange: (value: string) => void;
  onProjectChange: (value: string) => void;
  onScan: () => void;
};

export function SearchBar({
  query,
  project,
  projects,
  isScanning,
  onQueryChange,
  onProjectChange,
  onScan
}: Props) {
  return (
    <div className="toolbar">
      <label className="searchBox">
        <Search size={18} aria-hidden="true" />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search sessions"
          aria-label="Search sessions"
        />
      </label>
      <select value={project} onChange={(event) => onProjectChange(event.target.value)} aria-label="Project">
        <option value="">All projects</option>
        {projects.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <button className="iconButton primary" onClick={onScan} disabled={isScanning} title="Scan transcripts">
        <RefreshCw size={18} className={isScanning ? "spin" : ""} aria-hidden="true" />
        <span>{isScanning ? "Scanning" : "Scan"}</span>
      </button>
    </div>
  );
}

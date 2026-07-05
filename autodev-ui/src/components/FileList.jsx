export default function FileList({
  changes,
  selected,
  onSelect,
  rejected,
  onToggleReject,
}) {
  return (
    <div className="file-list">
      <div className="file-list-header">
        <span className="fl-label">Proposed changes</span>
        <span className="fl-count">{changes.length} files</span>
      </div>

      {changes.map((c, i) => {
        const isNew = !c.old_content;
        const isRejected = rejected.has(i);
        const isSelected = selected === i;

        return (
          <div
            key={i}
            className={`file-item ${isSelected ? "selected" : ""} ${isRejected ? "rejected" : ""}`}
            onClick={() => onSelect(i)}
          >
            <span className={`file-badge ${isNew ? "new" : "mod"}`}>
              {isNew ? "new" : "mod"}
            </span>
            <span className="file-name" title={c.file_path}>
              {basename(c.file_path)}
            </span>
            <button
              className={`reject-toggle ${isRejected ? "undo" : ""}`}
              title={isRejected ? "Include this file" : "Skip this file"}
              onClick={(e) => {
                e.stopPropagation();
                onToggleReject(i);
              }}
            >
              {isRejected ? "↩" : "✕"}
            </button>
          </div>
        );
      })}
    </div>
  );
}

function basename(path) {
  return path.replace(/\\/g, "/").split("/").pop();
}

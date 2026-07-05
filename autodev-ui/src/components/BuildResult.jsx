export default function BuildResult({ result, onDismiss }) {
  if (!result) return null;

  const allPassed = Object.values(result.maven_results || {}).every(
    (r) => typeof r === "string" && r.includes("BUILD SUCCESS"),
  );

  return (
    <div className={`build-result ${allPassed ? "pass" : "fail"}`}>
      <div className="build-header">
        <span className="build-icon">{allPassed ? "✓" : "✗"}</span>
        <strong>{allPassed ? "Build passed" : "Build failed"}</strong>
        <button
          className="btn-ghost small"
          onClick={onDismiss}
          style={{ marginLeft: "auto" }}
        >
          Dismiss
        </button>
      </div>

      <div className="build-files">
        {(result.files_changed || []).map((f, i) => (
          <div key={i} className="build-file-row">
            <span className="build-file-name">{basename(f.file)}</span>
            <span className="build-file-exp">{f.explanation}</span>
          </div>
        ))}
      </div>

      {Object.entries(result.maven_results || {}).map(([folder, output]) => {
        const passed =
          typeof output === "string" && output.includes("BUILD SUCCESS");
        return (
          <details key={folder} className="maven-details">
            <summary className={passed ? "maven-pass" : "maven-fail"}>
              {passed ? "✓" : "✗"} mvn test — {folder}
            </summary>
            <pre className="maven-log">
              {typeof output === "string"
                ? output
                : JSON.stringify(output, null, 2)}
            </pre>
          </details>
        );
      })}
    </div>
  );
}

function basename(path) {
  return (path || "").replace(/\\/g, "/").split("/").pop();
}

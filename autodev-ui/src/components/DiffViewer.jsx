/**
 * DiffViewer
 * Props:
 *   oldContent  string  original file content (empty string = new file)
 *   newContent  string  proposed file content
 */
export default function DiffViewer({ oldContent, newContent }) {
  const lines = computeDiff(
    oldContent ? oldContent.split("\n") : [],
    newContent ? newContent.split("\n") : [],
  );

  if (!lines.length) {
    return <div className="diff-empty">No changes</div>;
  }

  return (
    <div className="diff-viewer">
      <table className="diff-table">
        <tbody>
          {lines.map((line, i) => {
            if (line.type === "hunk") {
              return (
                <tr key={i} className="diff-hunk">
                  <td colSpan={4} className="hunk-label">
                    {line.text}
                  </td>
                </tr>
              );
            }
            return (
              <tr key={i} className={`diff-line diff-${line.type}`}>
                <td className="ln ln-old">{line.oldLn || ""}</td>
                <td className="ln ln-new">{line.newLn || ""}</td>
                <td className="diff-sign">
                  {line.type === "add" ? "+" : line.type === "rem" ? "−" : " "}
                </td>
                <td className="diff-code">
                  <code>{line.text}</code>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Minimal LCS-based diff.
 * Returns an array of { type: 'ctx'|'add'|'rem'|'hunk', text, oldLn, newLn }
 * with hunk headers inserted before each changed section.
 */
function computeDiff(oldLines, newLines) {
  const CONTEXT = 3;
  const edits = lcs(oldLines, newLines);

  // Group into hunks
  const result = [];
  let i = 0;
  while (i < edits.length) {
    if (edits[i].type === "ctx") {
      i++;
      continue;
    }
    // Changed section found — collect with context
    const start = Math.max(0, i - CONTEXT);
    const end = Math.min(edits.length, findEndOfHunk(edits, i) + CONTEXT);
    const hunkEdits = edits.slice(start, end);

    const oldStart = hunkEdits.find((e) => e.oldLn)?.oldLn ?? 1;
    const newStart = hunkEdits.find((e) => e.newLn)?.newLn ?? 1;
    const oldCount = hunkEdits.filter((e) => e.type !== "add").length;
    const newCount = hunkEdits.filter((e) => e.type !== "rem").length;

    result.push({
      type: "hunk",
      text: `@@ -${oldStart},${oldCount} +${newStart},${newCount} @@`,
    });
    hunkEdits.forEach((e) => result.push(e));
    i = end;
  }
  return result;
}

function findEndOfHunk(edits, start) {
  let end = start;
  for (let i = start; i < edits.length; i++) {
    if (edits[i].type !== "ctx") end = i;
  }
  return end;
}

function lcs(a, b) {
  const m = a.length,
    n = b.length;
  // dp[i][j] = length of LCS of a[0..i-1], b[0..j-1]
  const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1));
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);

  // Traceback
  const edits = [];
  let i = m,
    j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      edits.push({ type: "ctx", text: a[i - 1], oldLn: i, newLn: j });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      edits.push({ type: "add", text: b[j - 1], newLn: j });
      j--;
    } else {
      edits.push({ type: "rem", text: a[i - 1], oldLn: i });
      i--;
    }
  }
  return edits.reverse();
}

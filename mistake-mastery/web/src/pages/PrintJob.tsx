import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, PrintJobInfo } from "../api";
import { fmtTime, StatusBadge } from "../components/common";

// 打印单页面，也是 PDF 上二维码的落地页：孩子做完后，家长扫码逐题回填对错。
export default function PrintJobPage() {
  const { id } = useParams();
  const [job, setJob] = useState<PrintJobInfo | null>(null);
  const [results, setResults] = useState<Record<number, string>>({});
  const [saved, setSaved] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => api.get<PrintJobInfo>(`/api/print-jobs/${id}`).then(setJob), [id]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (!job || job.status === "ready" || job.status === "failed") return;
    const t = window.setInterval(load, 1500);
    return () => window.clearInterval(t);
  }, [job, load]);

  const submit = async () => {
    setError("");
    try {
      const r = await api.post<PrintJobInfo & { recorded: number }>(`/api/print-jobs/${id}/results`, {
        results: Object.entries(results).map(([seq, result]) => ({ seq: Number(seq), result })),
      });
      setJob(r);
      setSaved(r.recorded);
      setResults({});
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (!job) return <div className="muted">加载中…</div>;
  const gradable = (job.items ?? []).filter((i) => i.mistake_id);

  return (
    <>
      <div className="topbar">
        <h1>{job.title}</h1>
        <span className="muted small">{fmtTime(job.created_at)}</span>
      </div>
      <div className="card stack">
        {job.status === "ready" ? (
          <a className="btn primary block" href={`/api/print-jobs/${job.id}/pdf`} target="_blank" rel="noreferrer">
            📄 打开 PDF（{job.page_count} 页）
          </a>
        ) : job.status === "failed" ? (
          <div className="error">生成失败：{job.error}</div>
        ) : (
          <div className="muted">正在生成…</div>
        )}
        <p className="muted small">手机上打开 PDF 后，点"分享 → 打印"就能用家里的打印机（AirPrint）；也可以在电脑上打开打印。</p>
      </div>

      {!!gradable.length && (
        <div className="card stack">
          <h2>孩子做完了？逐题回填</h2>
          {gradable.map((it) => (
            <div key={it.seq} className="row spread">
              <span>
                <b>{it.seq}.</b> 原第 {it.number_label || "?"} 题{" "}
                {it.status && <StatusBadge status={it.status} name={it.status_name ?? undefined} />}
              </span>
              <span className="row" style={{ gap: 4 }}>
                {([["correct", "✓"], ["partial", "½"], ["wrong", "✗"]] as const).map(([v, n]) => (
                  <button key={v} className={`chip ${results[it.seq] === v ? "on" : ""}`}
                    onClick={() => setResults((r) => ({ ...r, [it.seq]: v }))}>{n}</button>
                ))}
              </span>
            </div>
          ))}
          {error && <div className="error">{error}</div>}
          {saved !== null && <div className="muted">已记录 {saved} 题，状态已更新。</div>}
          <button className="primary block" disabled={!Object.keys(results).length} onClick={submit}>
            保存 {Object.keys(results).length} 题的结果
          </button>
        </div>
      )}
      {job.template === "page_restore" && (
        <div className="card muted small">
          原卷还原单不对应具体错题。孩子做完后，可以到 <Link to="/mistakes">错题本</Link> 里逐题记录。
        </div>
      )}
    </>
  );
}

import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, Doc, MistakeSummary, PrintJobInfo, subjectName } from "../api";
import { fmtTime, JobProgress, StatusBadge, useJob, useStudent } from "../components/common";

export default function Print() {
  const { student } = useStudent();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [template, setTemplate] = useState<"redo_sheet" | "page_restore">(params.get("document") ? "page_restore" : "redo_sheet");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [docId, setDocId] = useState(params.get("document") ?? "");
  const [mistakes, setMistakes] = useState<MistakeSummary[]>([]);
  const [picked, setPicked] = useState<string[]>(params.get("mistakes")?.split(",").filter(Boolean) ?? []);
  const [withKey, setWithKey] = useState(false);
  const [extra, setExtra] = useState(0);
  const [jobs, setJobs] = useState<PrintJobInfo[]>([]);
  const [printId, setPrintId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Doc[]>(`/api/documents?student_id=${student.id}`).then((d) => {
      setDocs(d.filter((x) => x.status !== "processing"));
      if (!docId && d.length) setDocId(d[0].id);
    });
    api.get<MistakeSummary[]>(`/api/mistakes?student_id=${student.id}&status=TO_REDO,TO_TUTOR,TO_VARIANT,TO_REVIEW,STUBBORN`).then(setMistakes);
    api.get<PrintJobInfo[]>(`/api/print-jobs?student_id=${student.id}`).then(setJobs);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [student.id]);

  const job = useJob(taskId, () => printId && navigate(`/p/${printId}`));

  const create = async () => {
    setError("");
    try {
      const r = await api.post<{ print_job_id: string; job_id: string }>("/api/print-jobs", {
        student_id: student.id, template,
        document_id: template === "page_restore" ? docId : null,
        mistake_ids: template === "redo_sheet" ? picked : null,
        layout: { with_key: withKey, extra_space_mm: extra },
      });
      setPrintId(r.print_job_id);
      setTaskId(r.job_id);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const redoOnly = mistakes.filter((m) => m.status === "TO_REDO").map((m) => m.id);

  if (taskId) {
    return (
      <>
        <div className="topbar"><h1>正在生成 PDF</h1></div>
        <div className="card"><JobProgress job={job} /></div>
      </>
    );
  }

  return (
    <>
      <div className="topbar"><h1>打印</h1></div>
      <div className="seg" style={{ marginBottom: 10 }}>
        <button className={template === "redo_sheet" ? "on" : ""} onClick={() => setTemplate("redo_sheet")}>错题重做单</button>
        <button className={template === "page_restore" ? "on" : ""} onClick={() => setTemplate("page_restore")}>原卷还原</button>
      </div>

      {template === "page_restore" ? (
        <div className="card stack">
          <p className="muted small">打印擦除笔迹后的整张卷子，让孩子在原位置上重做。A3 双栏的卷子会自动拆成两页 A4。</p>
          <select value={docId} onChange={(e) => setDocId(e.target.value)}>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.title || subjectName(d.subject)} · {fmtTime(d.created_at)}</option>)}
          </select>
        </div>
      ) : (
        <div className="card stack">
          <div className="row spread">
            <span>已选 {picked.length} 题</span>
            <span className="row">
              <button className="chip" onClick={() => setPicked(redoOnly)}>选全部"待重做"</button>
              <button className="chip" onClick={() => setPicked([])}>清空</button>
            </span>
          </div>
          <p className="muted small">每道题按原卷大小打印，保留原来的作答空白；一道题不会跨页。</p>
          {mistakes.map((m) => (
            <label key={m.id} className={`list-item card ${picked.includes(m.id) ? "selected" : ""}`} style={{ margin: 0 }}>
              <input type="checkbox" checked={picked.includes(m.id)} onChange={() => toggle(m.id)} style={{ width: 22, height: 22, flex: "none" }} />
              {m.instance_id && <img className="thumb" style={{ width: 64, height: 64 }} loading="lazy" alt="" src={`/api/instances/${m.instance_id}/image?kind=erased&max_side=400`} />}
              <div className="body">
                <div className="row spread">
                  <span>{m.document?.title ?? subjectName(m.subject)} · 第 {m.number_label || "?"} 题</span>
                  <StatusBadge status={m.status} name={m.status_name} />
                </div>
                <div className="muted small clamp">{m.kp_names.map((n) => n.split(" › ").pop()).join("、")}</div>
              </div>
            </label>
          ))}
          {!mistakes.length && <div className="muted">还没有未学透的错题。</div>}
        </div>
      )}

      <div className="card stack">
        <label className="row"><input type="checkbox" checked={withKey} onChange={(e) => setWithKey(e.target.checked)} style={{ width: "auto" }} /> 附答案页（单独一页，可以先收起来）</label>
        {template === "redo_sheet" && (
          <label className="field">每题额外留白
            <select value={extra} onChange={(e) => setExtra(Number(e.target.value))}>
              <option value={0}>不额外留白（用原卷的空白）</option>
              <option value={30}>3 厘米</option>
              <option value={60}>6 厘米</option>
            </select>
          </label>
        )}
      </div>
      {error && <div className="error">{error}</div>}
      <button className="primary block" style={{ marginTop: 12 }} onClick={create}
        disabled={template === "redo_sheet" ? !picked.length : !docId}>
        生成 PDF
      </button>

      {!!jobs.length && (
        <div className="card" style={{ marginTop: 14 }}>
          <h2>打印记录</h2>
          {jobs.map((j) => (
            <Link key={j.id} to={`/p/${j.id}`} className="row spread" style={{ padding: "6px 0" }}>
              <span>{j.title}</span>
              <span className="muted small">{j.status === "ready" ? `${j.page_count} 页` : j.status} · {fmtTime(j.created_at)}</span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

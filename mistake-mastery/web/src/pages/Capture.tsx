import { ChangeEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Job, runtime, Subject, SUBJECTS } from "../api";
import { JobProgress, useCurriculum, useJob, useStudent } from "../components/common";

export default function Capture() {
  const { student } = useStudent();
  const navigate = useNavigate();
  const [subject, setSubject] = useState<Subject>("math");
  const [mode, setMode] = useState<"page" | "single">("page");
  const [sourceKind, setSourceKind] = useState("quiz");
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [docId, setDocId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const cur = useCurriculum(subject);

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [files]);

  const job = useJob(jobId, (j: Job) => {
    if (j.status === "done" && docId) navigate(`/documents/${docId}`);
  });

  const addFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []);
    setFiles((f) => [...f, ...picked]);
    e.target.value = "";
  };

  const upload = async () => {
    setUploading(true);
    setError("");
    const form = new FormData();
    form.append("student_id", student.id);
    form.append("subject", subject);
    form.append("mode", mode);
    form.append("source_kind", sourceKind);
    form.append("title", title);
    files.forEach((f) => form.append("files", f, f.name));
    try {
      const r = await api.upload<{ document_id: string; job_id: string }>("/api/captures", form);
      setDocId(r.document_id);
      setJobId(r.job_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  if (jobId) {
    return (
      <>
        <div className="topbar"><h1>正在处理</h1></div>
        <div className="card stack">
          <JobProgress job={job} />
          <p className="muted">矫正、识别题目、擦除笔迹，每页大约半分钟。可以先离开，处理完会出现在首页"待处理的卷子"里。</p>
          {job?.status === "failed" && docId && (
            <button onClick={() => navigate(`/documents/${docId}`)}>查看详情</button>
          )}
        </div>
      </>
    );
  }

  return (
    <>
      <div className="topbar"><h1>拍照录入</h1></div>
      <div className="card stack">
        <div className="seg">
          {SUBJECTS.map((s) => (
            <button key={s.code} className={subject === s.code ? "on" : ""} onClick={() => setSubject(s.code)}>{s.name}</button>
          ))}
        </div>
        <div className="seg">
          <button className={mode === "page" ? "on" : ""} onClick={() => setMode("page")}>整页（自动切题）</button>
          <button className={mode === "single" ? "on" : ""} onClick={() => setMode("single")}>单题</button>
        </div>
        <div className="row">
          <label className="field" style={{ flex: 1 }}>来源
            <select value={sourceKind} onChange={(e) => setSourceKind(e.target.value)}>
              {cur?.source_kinds.map((k) => <option key={k.code} value={k.code}>{k.name}</option>)}
            </select>
          </label>
          <label className="field" style={{ flex: 2 }}>名称（选填，能从卷头识别）
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="如：海淀期中" />
          </label>
        </div>
      </div>

      <div className="card stack">
        <div className="row spread">
          <h2 style={{ margin: 0 }}>照片（{files.length}）</h2>
          {!!files.length && <button className="chip" onClick={() => setFiles([])}>清空</button>}
        </div>
        <p className="muted small">平放在深色桌面上、光线均匀、整页入镜。一份卷子的多页按顺序拍。</p>
        <div className="row">
          {previews.map((u, i) => (
            <div key={u} style={{ position: "relative" }}>
              <img src={u} className="thumb" alt={`第 ${i + 1} 页`} />
              <button className="chip" style={{ position: "absolute", top: -6, right: -6, minHeight: 24, padding: "0 6px" }}
                onClick={() => setFiles((f) => f.filter((_, j) => j !== i))}>✕</button>
            </div>
          ))}
        </div>
        <div className="row">
          <label className="btn" style={{ flex: 1 }}>
            📷 拍照
            <input type="file" accept="image/*" capture="environment" onChange={addFiles} hidden />
          </label>
          <label className="btn" style={{ flex: 1 }}>
            🖼 从相册选
            <input type="file" accept="image/*" multiple onChange={addFiles} hidden />
          </label>
        </div>
        {runtime.sampleFiles && (
          <button className="block" onClick={async () => setFiles(await runtime.sampleFiles!())}>
            🧪 用示例照片（预览版）
          </button>
        )}
      </div>

      {error && <div className="error">{error}</div>}
      <button className="primary block" style={{ marginTop: 12 }} disabled={!files.length || uploading} onClick={upload}>
        {uploading ? "上传中…" : `上传并识别 ${files.length} 页`}
      </button>
    </>
  );
}

import { createContext, CSSProperties, ReactNode, useContext, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { api, Curriculum, getCurriculum, Job, KpNode, runtime, Student, Subject } from "../api";

// ---------------------------------------------------------------- 当前孩子

export interface StudentCtx {
  student: Student;
  students: Student[];
  setStudentId: (id: string) => void;
  reload: () => Promise<void>;
}
export const StudentContext = createContext<StudentCtx | null>(null);
export function useStudent(): StudentCtx {
  const ctx = useContext(StudentContext);
  if (!ctx) throw new Error("StudentContext missing");
  return ctx;
}

// ---------------------------------------------------------------- 题目文本（Markdown + 公式）

export function Md({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {text}
      </ReactMarkdown>
    </div>
  );
}

// ---------------------------------------------------------------- 后台任务进度

export function useJob(jobId: string | null, onDone?: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    if (!jobId) return;
    let stop = false;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const j = await api.get<Job>(`/api/jobs/${jobId}`);
        if (stop) return;
        setJob(j);
        if (j.status === "done" || j.status === "failed") {
          onDone?.(j);
          return;
        }
      } catch {
        /* 网络抖动：下次再试 */
      }
      timer = window.setTimeout(tick, 1200);
    };
    tick();
    return () => {
      stop = true;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);
  return job;
}

export function JobProgress({ job }: { job: Job | null }) {
  if (!job) return <div className="muted">排队中…</div>;
  const pct = job.status === "done" ? 100 : job.progress?.pct ?? 0;
  return (
    <div className="stack">
      <div className="row spread">
        <span>{job.status === "failed" ? "处理失败" : job.progress?.stage ?? "处理中"}</span>
        <span className="muted">{pct}%</span>
      </div>
      <div className="progress">
        <div style={{ width: `${pct}%` }} />
      </div>
      {job.error && <div className="error">{job.error}</div>}
    </div>
  );
}

// ---------------------------------------------------------------- 字典

export function useCurriculum(subject: Subject | undefined): Curriculum | null {
  const [cur, setCur] = useState<Curriculum | null>(null);
  useEffect(() => {
    if (subject) getCurriculum(subject).then(setCur);
  }, [subject]);
  return cur;
}

export function StatusBadge({ status, name }: { status: string; name?: string }) {
  return <span className={`badge ${status}`}>{name ?? status}</span>;
}

// ---------------------------------------------------------------- 知识点选择

function TreeNode({ node, selected, toggle }: { node: KpNode; selected: string[]; toggle: (c: string) => void }) {
  const on = selected.includes(node.code);
  const label = (
    <label className="row" style={{ gap: 6 }}>
      <input type="checkbox" checked={on} onChange={() => toggle(node.code)} style={{ width: "auto" }} />
      <span>{node.name}</span>
    </label>
  );
  if (!node.children.length) return <div style={{ marginLeft: 10, padding: "3px 0" }}>{label}</div>;
  return (
    <details open={node.children.some((c) => selected.some((s) => s.startsWith(c.code)))}>
      <summary>{node.name}</summary>
      <div style={{ marginLeft: 10, padding: "3px 0" }}>{label}</div>
      {node.children.map((c) => (
        <TreeNode key={c.code} node={c} selected={selected} toggle={toggle} />
      ))}
    </details>
  );
}

export function KpPicker({ subject, value, onClose }: { subject: Subject; value: string[]; onClose: (v: string[] | null) => void }) {
  const cur = useCurriculum(subject);
  const [sel, setSel] = useState<string[]>(value);
  const toggle = (c: string) =>
    setSel((s) => (s.includes(c) ? s.filter((x) => x !== c) : s.length >= 3 ? s : [...s, c]));
  return (
    <div className="modal-bg" onClick={() => onClose(null)}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="row spread">
          <h2 style={{ margin: 0, fontSize: 17 }}>选择知识点（最多 3 个，第一个为主）</h2>
          <button onClick={() => onClose(sel)} className="primary">
            确定
          </button>
        </div>
        <div className="row" style={{ margin: "10px 0" }}>
          {sel.map((c) => (
            <button key={c} className="chip on" onClick={() => toggle(c)}>
              {cur?.names[c]?.split(" › ").pop() ?? c} ✕
            </button>
          ))}
        </div>
        <div className="tree">
          {cur?.tree.map((n) => <TreeNode key={n.code} node={n} selected={sel} toggle={toggle} />) ?? "加载中…"}
        </div>
      </div>
    </div>
  );
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return iso.slice(0, 16).replace("T", " ");
}

// ---------------------------------------------------------------- 错因选择（默认只显示已选和 AI 建议的）

export function CauseChips({ causes, value, suggested = [], onChange }: {
  causes: { code: string; name: string; hint: string }[];
  value: string[];
  suggested?: string[];
  onChange: (v: string[]) => void;
}) {
  const [all, setAll] = useState(false);
  const shown = all ? causes : causes.filter((c) => value.includes(c.code) || suggested.includes(c.code));
  return (
    <div className="row">
      <span className="muted small">错因</span>
      {shown.map((c) => {
        const on = value.includes(c.code);
        return (
          <button key={c.code} className={`chip ${on ? "on" : ""}`} title={c.hint}
            onClick={() => onChange(on ? value.filter((x) => x !== c.code) : [...value, c.code])}>
            {c.name}{suggested.includes(c.code) ? " ·AI" : ""}
          </button>
        );
      })}
      <button className="chip" onClick={() => setAll(!all)}>{all ? "收起" : shown.length ? "＋ 其他" : "＋ 选择错因"}</button>
    </div>
  );
}

// ---------------------------------------------------------------- 需要确认的操作

// 点一次变成"再点一次确认"，几秒内再点才执行（不用浏览器自带的 confirm 弹窗）。
export function ConfirmButton({ children, prompt, onConfirm, className = "danger", style }: {
  children: ReactNode;
  prompt: string;
  onConfirm: () => void;
  className?: string;
  style?: CSSProperties;
}) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = window.setTimeout(() => setArmed(false), 4000);
    return () => window.clearTimeout(t);
  }, [armed]);
  return (
    <button className={`${className} ${armed ? "armed" : ""}`} style={style}
      onClick={() => { if (armed) { setArmed(false); onConfirm(); } else setArmed(true); }}>
      {armed ? prompt : children}
    </button>
  );
}

// ---------------------------------------------------------------- 看大图

export function ImageViewer({ src, title, onClose }: { src: string; title: string; onClose: () => void }) {
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal stack" onClick={(e) => e.stopPropagation()}>
        <div className="row spread">
          <b>{title}</b>
          <button className="chip" onClick={onClose}>关闭</button>
        </div>
        <img className="crop" src={src} alt={title} />
        {!runtime.demo && <a className="small" href={src} target="_blank" rel="noreferrer">在新窗口打开原图（可放大）</a>}
      </div>
    </div>
  );
}

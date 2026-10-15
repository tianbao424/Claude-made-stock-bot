import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, KnowledgeDetail as Detail, MASTERY_NAMES, runtime, subjectName } from "../api";
import { StatusBadge, useStudent } from "../components/common";
import { MasteryBar } from "./Knowledge";

const monthDay = (iso: string) => `${Number(iso.slice(5, 7))} 月 ${Number(iso.slice(8, 10))} 日`;

export default function KnowledgeDetail() {
  const { code } = useParams();
  const { student } = useStudent();
  const navigate = useNavigate();
  const [d, setD] = useState<Detail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setD(null);
    api.get<Detail>(`/api/knowledge/${code}?student_id=${student.id}`).then(setD).catch((e) => setError(e.message));
  }, [code, student.id]);

  if (error) return <div className="error">{error}</div>;
  if (!d) return <div className="muted">加载中…</div>;
  const open = d.mistake_list.filter((m) => m.status !== "MASTERED");
  const parents = d.path.split(" › ").slice(0, -1);

  return (
    <>
      <div className="topbar">
        <h1>{d.name}</h1>
      </div>
      <div className="muted small" style={{ marginTop: -6, marginBottom: 10 }}>
        {subjectName(d.subject)}{parents.length ? ` · ${parents.join(" › ")}` : ""}
        {d.weight !== null ? ` · 中考权重 ${Math.round(d.weight * 100)}%` : ""}
      </div>

      <div className={`card row lvl-${d.status}`} style={{ gap: 16, alignItems: "center", flexWrap: "nowrap" }}>
        <div style={{ textAlign: "center", minWidth: 72 }}>
          <div className="big-num">{d.mastery === null ? "—" : Math.round(d.mastery * 100)}</div>
          <div className="small" style={{ color: "var(--lvl)" }}>{MASTERY_NAMES[d.status]}</div>
        </div>
        <div className="small" style={{ minWidth: 0 }}>
          {d.mistakes ? (
            <>
              <div>错题 {d.mistakes} 道：未学透 {d.open}，已学透 {d.mastered}{d.stubborn ? `，顽固 ${d.stubborn}` : ""}{d.repeat ? `，反复错 ${d.repeat}` : ""}</div>
              <div className="muted">按 {d.observations} 次作答算出{d.last_wrong_at ? `，最近一次做错在 ${monthDay(d.last_wrong_at)}` : ""}</div>
            </>
          ) : (
            <div className="muted">还没有这个考点的错题记录。不一定是会了，可以拿下面题库里的同类题测一测。</div>
          )}
        </div>
      </div>

      {!!d.causes.length && (
        <div className="card">
          <h2>错因</h2>
          <div className="row">{d.causes.map((c) => <span key={c.code} className="chip">{c.name} × {c.n}</span>)}</div>
        </div>
      )}

      {!!d.mistake_list.length && (
        <div className="row" style={{ margin: "10px 0" }}>
          {!!open.length && (
            <button className="primary" style={{ flex: 1 }} onClick={() => navigate(`/print?mistakes=${open.map((m) => m.id).join(",")}`)}>
              🖨 打印这 {open.length} 道未学透的题
            </button>
          )}
          <Link to={`/mistakes?kp=${d.code}`} className="btn" style={{ flex: open.length ? "none" : 1 }}>在错题本里看</Link>
        </div>
      )}

      {!!d.children.length && (
        <div className="card">
          <h2>下面的考点</h2>
          {d.children.map((c) => {
            const body = (
              <>
                <span className="name">{c.name}</span>
                <span className="meta">{c.mistakes ? (c.open ? `未学透 ${c.open} / ${c.mistakes}` : `${c.mistakes} 道已学透`) : c.bank ? `题库 ${c.bank}` : ""}</span>
                <MasteryBar node={c} />
              </>
            );
            return c.mistakes || c.bank
              ? <Link key={c.code} to={`/knowledge/${c.code}`} className="kp-row">{body}</Link>
              : <div key={c.code} className="kp-row muted">{body}</div>;
          })}
        </div>
      )}

      {!!d.mistake_list.length && (
        <div className="card">
          <h2>错题（{d.mistake_list.length}）</h2>
          {d.mistake_list.map((m) => (
            <Link key={m.id} to={`/mistakes/${m.id}`} className="list-item kp-row" style={{ alignItems: "flex-start" }}>
              {m.instance_id && <img className="thumb" style={{ width: 64, height: 64 }} loading="lazy" alt=""
                src={runtime.fileUrl(`/api/instances/${m.instance_id}/image?kind=erased&max_side=400`)} />}
              <div className="body">
                <div className="row spread">
                  <span>{m.document?.title ?? "未命名"} · 第 {m.number_label || "?"} 题</span>
                  <StatusBadge status={m.status} name={m.status_name} />
                </div>
                <div className="muted small">错 {m.wrong_count} 次{m.round > 1 ? ` · 第 ${m.round} 轮` : ""}</div>
              </div>
            </Link>
          ))}
        </div>
      )}

      <div className="card">
        <h2>题库里的同类题（{d.bank_questions.length}）</h2>
        {d.bank_questions.length ? d.bank_questions.map((b) => (
          <Link key={b.id} to={`/bank/${b.paper_id}`} className="list-item kp-row" style={{ alignItems: "flex-start" }}>
            <img className="thumb" style={{ width: 64, height: 64 }} loading="lazy" alt=""
              src={runtime.fileUrl(`/api/bank/questions/${b.id}/image?max_side=400`)} />
            <div className="body">
              <div>{b.paper_title} · 第 {b.number_label} 题</div>
              <div className="muted small">{b.primary ? "主要考这个知识点" : "也涉及这个知识点"}{b.done ? " · 孩子做错过" : ""}</div>
            </div>
          </Link>
        )) : <div className="muted small">题库里还没有这个知识点的题。导入真题和区统考卷子后，这里会列出同类题。</div>}
      </div>
    </>
  );
}

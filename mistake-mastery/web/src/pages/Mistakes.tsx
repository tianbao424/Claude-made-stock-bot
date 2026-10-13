import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, MistakeSummary, SUBJECTS } from "../api";
import { StatusBadge, useStudent } from "../components/common";

const STATUS_FILTERS = [
  ["", "全部"], ["TO_REDO", "待重做"], ["TO_TUTOR", "待讲解"], ["TO_VARIANT", "待变式"], ["TO_REVIEW", "待复习"],
  ["MASTERED", "已学透"], ["STUBBORN", "顽固"],
];

export default function Mistakes() {
  const { student } = useStudent();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const subject = params.get("subject") ?? "";
  const status = params.get("status") ?? "";
  const [list, setList] = useState<MistakeSummary[] | null>(null);
  const [picking, setPicking] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);

  useEffect(() => {
    setList(null);
    const q = new URLSearchParams({ student_id: student.id });
    if (subject) q.set("subject", subject);
    if (status) q.set("status", status);
    api.get<MistakeSummary[]>(`/api/mistakes?${q}`).then(setList);
  }, [student.id, subject, status]);

  const setFilter = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };
  const togglePick = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  return (
    <>
      <div className="topbar">
        <h1>错题本</h1>
        <button className="chip" onClick={() => { setPicking(!picking); setPicked([]); }}>{picking ? "取消选择" : "选题打印"}</button>
      </div>
      <div className="row" style={{ marginBottom: 6 }}>
        <button className={`chip ${!subject ? "on" : ""}`} onClick={() => setFilter("subject", "")}>全部学科</button>
        {SUBJECTS.map((s) => (
          <button key={s.code} className={`chip ${subject === s.code ? "on" : ""}`} onClick={() => setFilter("subject", s.code)}>{s.name}</button>
        ))}
      </div>
      <div className="row" style={{ marginBottom: 10 }}>
        {STATUS_FILTERS.map(([v, n]) => (
          <button key={v} className={`chip ${status === v ? "on" : ""}`} onClick={() => setFilter("status", v)}>{n}</button>
        ))}
      </div>

      {list === null && <div className="muted">加载中…</div>}
      {list?.length === 0 && <div className="card muted">这里还没有题。</div>}
      {list?.map((m) => {
        const body = (
          <div className="list-item">
            {m.instance_id && <img className="thumb" loading="lazy" alt="" src={`/api/instances/${m.instance_id}/image?kind=erased&max_side=400`} />}
            <div className="body">
              <div className="row spread">
                <b>{m.document?.title ?? "未命名"} · 第 {m.number_label || "?"} 题</b>
                <StatusBadge status={m.status} name={m.status_name} />
              </div>
              <div className="muted small clamp">{m.kp_names.map((n) => n.split(" › ").pop()).join("、") || "未分类"}</div>
              <div className="muted small">
                错 {m.wrong_count} 次{m.round > 1 ? ` · 第 ${m.round} 轮` : ""}
              </div>
            </div>
          </div>
        );
        return picking ? (
          <div key={m.id} className={`card ${picked.includes(m.id) ? "selected" : ""}`} onClick={() => togglePick(m.id)}>{body}</div>
        ) : (
          <Link key={m.id} to={`/mistakes/${m.id}`} className="card" style={{ display: "block", color: "inherit" }}>{body}</Link>
        );
      })}

      {picking && (
        <button className="primary block" style={{ position: "sticky", bottom: 80, marginTop: 12 }} disabled={!picked.length}
          onClick={() => navigate(`/print?mistakes=${picked.join(",")}`)}>
          打印 {picked.length} 道题的重做单
        </button>
      )}
    </>
  );
}

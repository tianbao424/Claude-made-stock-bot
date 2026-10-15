import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, BlindSpot, KnowledgeNode, KnowledgeOverview, MASTERY_NAMES, Subject, SUBJECTS } from "../api";
import { useStudent } from "../components/common";

export function MasteryPill({ node }: { node: { status: KnowledgeNode["status"]; mastery: number | null } }) {
  return (
    <span className={`lvl-pill lvl-${node.status}`}>
      {MASTERY_NAMES[node.status]}{node.mastery !== null ? ` ${Math.round(node.mastery * 100)}` : ""}
    </span>
  );
}

export function MasteryBar({ node }: { node: KnowledgeNode }) {
  return (
    <span className={`kp-bar lvl-${node.status}`} title={MASTERY_NAMES[node.status]}>
      <div style={{ width: node.mastery === null ? 0 : `${Math.max(6, node.mastery * 100)}%` }} />
    </span>
  );
}

export function BlindSpotRow({ b, showSubject }: { b: BlindSpot; showSubject?: boolean }) {
  return (
    <Link to={`/knowledge/${b.code}`} className="kp-row" style={{ alignItems: "flex-start" }}>
      <div className="name">
        <div className="row spread" style={{ gap: 6, flexWrap: "nowrap" }}>
          <b style={{ minWidth: 0 }}>{b.name}</b>
          <MasteryPill node={b} />
        </div>
        <div className="muted small clamp">{showSubject ? `${b.subject === "math" ? "数学" : "物理"} · ` : ""}{b.path.split(" › ").slice(0, -1).join(" › ")}</div>
        <div className="reason">{b.reasons.join(" · ")}</div>
      </div>
      <span className="muted">›</span>
    </Link>
  );
}

function counts(n: KnowledgeNode): string {
  if (!n.mistakes) return n.bank ? `题库 ${n.bank}` : "";
  return n.open ? `未学透 ${n.open} / ${n.mistakes}` : `${n.mistakes} 道已学透`;
}

function Row({ n, depth }: { n: KnowledgeNode; depth: number }) {
  const body = (
    <>
      <span className="name">{n.name}</span>
      <span className="meta">{counts(n)}</span>
      <MasteryBar node={n} />
    </>
  );
  const cls = `kp-row l${Math.min(depth, 3)}`;
  return n.mistakes || n.bank ? <Link to={`/knowledge/${n.code}`} className={cls}>{body}</Link> : <div className={`${cls} muted`}>{body}</div>;
}

function Module({ m }: { m: KnowledgeNode }) {
  const rows: { n: KnowledgeNode; depth: number }[] = [];
  // 主题都列出来；更细的考点只在这个主题有错题或题库题时展开，免得一屏全是灰的
  const walk = (n: KnowledgeNode, depth: number) => {
    rows.push({ n, depth });
    if (n.mistakes || n.bank) (n.children ?? []).forEach((c) => walk(c, depth + 1));
  };
  (m.children ?? []).forEach((c) => walk(c, 2));
  return (
    <details className="kp-module" open={m.mistakes > 0}>
      <summary className="kp-row" style={{ borderTop: 0 }}>
        <b className="name">{m.name}</b>
        <span className="meta">{counts(m)}</span>
        <MasteryBar node={m} />
      </summary>
      <div style={{ paddingBottom: 6 }}>{rows.map(({ n, depth }) => <Row key={n.code} n={n} depth={depth} />)}</div>
    </details>
  );
}

export default function Knowledge() {
  const { student } = useStudent();
  const [params, setParams] = useSearchParams();
  const subject = (params.get("subject") as Subject) || "math";
  const [data, setData] = useState<KnowledgeOverview | null>(null);

  useEffect(() => {
    setData(null);
    api.get<KnowledgeOverview>(`/api/knowledge?student_id=${student.id}&subject=${subject}`).then(setData);
  }, [student.id, subject]);

  const sum = data?.summary;
  return (
    <>
      <div className="topbar">
        <h1>知识点</h1>
        <Link to="/mistakes" className="chip btn">按错题看</Link>
      </div>
      <div className="seg" style={{ marginBottom: 10 }}>
        {SUBJECTS.map((s) => (
          <button key={s.code} className={subject === s.code ? "on" : ""}
            onClick={() => setParams({ subject: s.code }, { replace: true })}>{s.name}</button>
        ))}
      </div>

      {!data && <div className="muted">加载中…</div>}
      {data && sum && (
        <>
          <div className="stat-grid">
            <div className="stat lvl-weak"><b style={{ color: "var(--lvl)" }}>{sum.weak}</b><span className="muted">薄弱</span></div>
            <div className="stat lvl-medium"><b style={{ color: "var(--lvl)" }}>{sum.medium}</b><span className="muted">待加强</span></div>
            <div className="stat lvl-good"><b style={{ color: "var(--lvl)" }}>{sum.good}</b><span className="muted">较好</span></div>
          </div>
          <p className="muted small">
            已涉及 {sum.points} 个考点 · 未学透的错题 {sum.open} 道 · 已学透 {sum.mastered} 道。
            掌握度按每次作答算，最近的、难题的权重更高；录入时做错也算一次。
          </p>

          <div className="card">
            <h2>掌握死角</h2>
            {data.blind_spots.length ? data.blind_spots.map((b) => <BlindSpotRow key={b.code} b={b} />) : (
              <div className="muted small">{sum.points ? "目前没有明显的死角：错题都学透了，最近也做得不错。" : "还没有错题数据。卷子发回来后拍照录入，这里就会出现需要补的考点。"}</div>
            )}
          </div>

          <div className="card">
            <div className="row spread">
              <h2 style={{ margin: 0 }}>知识点地图</h2>
              <span className="row small" style={{ gap: 6 }}>
                {(["weak", "medium", "good", "none"] as const).map((l) => <span key={l} className={`lvl-pill lvl-${l}`}>{MASTERY_NAMES[l]}</span>)}
              </span>
            </div>
            <div style={{ marginTop: 6 }}>{data.tree.map((m) => <Module key={m.code} m={m} />)}</div>
          </div>

          {!!data.untouched.length && (
            <details className="card">
              <summary><b>还没有错题记录的常考点（{data.untouched.length}）</b></summary>
              <p className="muted small">没有错题不一定是会了，也可能是还没学到、还没考到。可以用题库里的同类题测一测。</p>
              {data.untouched.map((u) => {
                const body = (
                  <>
                    <span className="name">{u.name}<span className="muted small"> · {u.path.split(" › ")[0]}</span></span>
                    <span className="meta">{u.bank ? `题库 ${u.bank} 道 ›` : ""}</span>
                  </>
                );
                return u.bank
                  ? <Link key={u.code} to={`/knowledge/${u.code}`} className="kp-row">{body}</Link>
                  : <div key={u.code} className="kp-row">{body}</div>;
              })}
            </details>
          )}
        </>
      )}
    </>
  );
}

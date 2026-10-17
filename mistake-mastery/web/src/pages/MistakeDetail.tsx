import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ANSWER_SOURCE, api, GRADING, Job, MistakeDetail as Detail, runtime } from "../api";
import { CauseChips, ConfirmButton, fmtTime, JobProgress, KpPicker, Md, StatusBadge, useCurriculum, useJob } from "../components/common";

const CONTEXT: Record<string, string> = { capture: "录入", redo: "重做", variant: "变式", review: "复习", exam_pack: "考前打印", daily: "每日学透单" };
const RESULT: Record<string, string> = { correct: "✓ 做对", wrong: "✗ 做错", partial: "½ 半对" };

export default function MistakeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [m, setM] = useState<Detail | null>(null);
  const [orig, setOrig] = useState(false);
  const [imgVer, setImgVer] = useState(0); // 重新擦除后换个地址，绕过浏览器缓存的旧图
  const [editAnswer, setEditAnswer] = useState<string | null>(null);
  const [kpOpen, setKpOpen] = useState(false);
  const [solveJob, setSolveJob] = useState<string | null>(null);
  const [error, setError] = useState("");
  const cur = useCurriculum(m?.subject);

  const load = useCallback(() => api.get<Detail>(`/api/mistakes/${id}`).then(setM), [id]);
  useEffect(() => {
    load();
  }, [load]);
  const job = useJob(solveJob, (j: Job) => {
    if (j.status === "done") load();
  });

  const act = async (fn: () => Promise<unknown>) => {
    setError("");
    try {
      await fn();
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (!m) return <div className="muted">加载中…</div>;
  const q = m.question;
  const pageId = m.instances?.find((i) => i.id === m.instance_id)?.page_id ?? null;
  const g = m.gates ?? {};

  return (
    <>
      <div className="topbar">
        <h1>{m.document?.title ?? "错题"} · 第 {m.number_label || "?"} 题</h1>
        <StatusBadge status={m.status} name={m.status_name} />
      </div>

      <div className="card stack">
        {m.instance_id && (
          <>
            <img className="crop" alt="" src={runtime.fileUrl(`/api/instances/${m.instance_id}/image?kind=${orig ? "original" : "erased"}${imgVer ? `&v=${imgVer}` : ""}`)} onClick={() => setOrig(!orig)} />
            <div className="row spread">
              <span className="muted small">点图片切换{orig ? "擦除后" : "原图（含孩子的作答和批改）"}</span>
              {pageId && (
                <button className="chip small" onClick={() => act(async () => {
                  await api.post(`/api/pages/${pageId}/erase`);
                  setImgVer(Date.now());
                })}>重新擦除这一页</button>
              )}
            </div>
          </>
        )}
        <div className="gates">
          <span className="muted">学透进度</span>
          <span className={`gate ${g.original ? "ok" : ""}`}>原题关{g.original ? " ✓" : ""}</span>→
          <span className={`gate ${g.variant ? "ok" : ""}`}>变式关{g.variant ? " ✓" : ""}</span>→
          <span className={`gate ${g.spaced ? "ok" : ""}`}>时间关{g.spaced ? " ✓" : ""}</span>
        </div>
        <div className="muted small">错 {m.wrong_count} 次 · 第 {m.round} 轮{m.next_review_at ? ` · 复习日 ${m.next_review_at}` : ""}</div>
        {m.bank && (
          <div className="small">📚 出处：<Link to={`/bank/${m.bank.paper_id}`}>{m.bank.paper_title}</Link> 第 {m.bank.number_label} 题</div>
        )}
      </div>

      <div className="card stack">
        <h2>记录这次重做的结果</h2>
        <div className="row">
          {(["correct", "partial", "wrong"] as const).map((r) => (
            <button key={r} style={{ flex: 1 }} onClick={() => act(() => api.post(`/api/mistakes/${m.id}/attempts`, { result: r, context: "redo" }))}>
              {RESULT[r]}
            </button>
          ))}
        </div>
        <p className="muted small">做对进入下一关；做错会转到"待讲解"。变式题和 AI 讲解在后续版本加入。</p>
      </div>

      <div className="card stack">
        <div className="row spread">
          <h2 style={{ margin: 0 }}>答案</h2>
          <span className="muted small">{ANSWER_SOURCE[q.answer_source] ?? q.answer_source}</span>
        </div>
        {editAnswer === null ? (
          <>
            <Md text={q.answer?.final || "（暂无）"} />
            {q.solution_md && (
              <details>
                <summary className="muted small">{q.answer_source === "official" ? "评分标准 / 解析" : `解答过程${q.answer_source.startsWith("ai") ? "（AI 生成，请核对）" : ""}`}</summary>
                <Md text={q.solution_md} />
              </details>
            )}
            <div className="row">
              <button className="chip" onClick={() => setEditAnswer(q.answer?.final ?? "")}>修改答案</button>
              {!["teacher", "manual", "answer_key", "official"].includes(q.answer_source) && (
                <button className="chip" onClick={() => act(async () => setSolveJob((await api.post<{ job_id: string }>(`/api/mistakes/${m.id}/solve`)).job_id))}>
                  请 AI 重新解答
                </button>
              )}
            </div>
            {solveJob && job?.status !== "done" && <JobProgress job={job} />}
          </>
        ) : (
          <div className="stack">
            <input value={editAnswer} onChange={(e) => setEditAnswer(e.target.value)} placeholder="正确答案" />
            <div className="row">
              <button className="primary" onClick={() => act(async () => { await api.patch(`/api/mistakes/${m.id}`, { answer: editAnswer }); setEditAnswer(null); })}>保存</button>
              <button onClick={() => setEditAnswer(null)}>取消</button>
            </div>
          </div>
        )}
      </div>

      {q.stem_md && (
        <div className="card">
          <h2>题目文字</h2>
          <Md text={q.stem_md} />
          {q.options?.map((o) => <Md key={o.key} text={`${o.key}. ${o.md}`} />)}
          {q.sub_questions?.map((s) => <Md key={s.no} text={`${s.no} ${s.md}`} />)}
        </div>
      )}

      <div className="card stack">
        <div className="row spread">
          <h2 style={{ margin: 0 }}>分类</h2>
          <button className="chip" onClick={() => setKpOpen(true)}>修改知识点</button>
        </div>
        <div className="row">{m.kp_names.map((n) => <span key={n} className="chip">{n.split(" › ").slice(-2).join(" › ")}</span>)}</div>
        {cur && (
          <CauseChips causes={cur.error_causes} value={m.error_causes}
            onChange={(v) => act(() => api.patch(`/api/mistakes/${m.id}`, { error_causes: v }))} />
        )}
      </div>

      <div className="card">
        <h2>错题旅程</h2>
        <ul className="timeline">
          {m.attempts.map((a) => (
            <li key={a.id}>
              <span className="muted small">{fmtTime(a.created_at)}</span> 第 {a.round} 轮 · {CONTEXT[a.context] ?? a.context} {RESULT[a.result] ?? a.result}
              {a.context === "capture" && m.instances[0]?.grading ? `（${GRADING[m.instances[0].grading] ?? ""}）` : ""}
            </li>
          ))}
        </ul>
      </div>

      {error && <div className="error">{error}</div>}
      <ConfirmButton className="danger block" style={{ marginTop: 10 }} prompt="再点一次，确认删除"
        onConfirm={() => act(async () => { await api.del(`/api/mistakes/${m.id}`); navigate("/mistakes"); })}>
        删除这道错题
      </ConfirmButton>

      {kpOpen && (
        <KpPicker subject={m.subject} value={m.kp_codes}
          onClose={(v) => { setKpOpen(false); if (v) act(() => api.patch(`/api/mistakes/${m.id}`, { kp_codes: v })); }} />
      )}
    </>
  );
}

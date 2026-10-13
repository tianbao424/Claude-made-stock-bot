import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ANSWER_SOURCE, api, BankPaperInfo, BankQuestion, runtime } from "../api";
import { ConfirmButton, JobProgress, Md, useCurriculum, useJob } from "../components/common";
import { paperMeta } from "./Bank";

const TYPE_NAMES: Record<string, string> = {
  choice_single: "单选", choice_multi: "多选", fill: "填空", solve: "解答", experiment: "实验探究", reading: "科普阅读",
  calc: "计算",
};

function QuestionCard({ q, kpName, onChange }: { q: BankQuestion; kpName: (c: string) => string; onChange: (q: BankQuestion) => void }) {
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState("");
  const v = q.verification ?? {};
  const patch = async (body: Record<string, unknown>) => {
    setError("");
    try {
      onChange(await api.patch<BankQuestion>(`/api/bank/questions/${q.id}`, body));
      setEditing(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className={`card stack ${q.needs_review ? "selected" : ""}`}>
      <div className="row spread">
        <b>第 {q.number_label || "?"} 题</b>
        <span className="muted small">
          {TYPE_NAMES[q.type] ?? q.type}{q.points ? ` · ${q.points}` : ""} · 第 {q.pages.join("–")} 页
        </span>
      </div>
      <img className="crop" loading="lazy" alt="" src={runtime.fileUrl(`/api/bank/questions/${q.id}/image`)} />
      {!!q.kp_codes.length && (
        <div className="row">{q.kp_codes.map((c) => <span key={c} className="chip">{kpName(c)}</span>)}</div>
      )}

      {editing === null ? (
        <div>
          <div className="row spread">
            <span><span className="muted small">答案</span> {q.answer?.final ? "" : "（暂无）"}</span>
            <span className="muted small">{ANSWER_SOURCE[q.answer_source] ?? q.answer_source}</span>
          </div>
          {q.answer?.final && <Md text={q.answer.final} />}
          {q.solution_md && (
            <details>
              <summary className="muted small">{q.answer_source === "ai_unverified" ? "AI 解答过程（请核对）" : "评分标准 / 解析"}</summary>
              <Md text={q.solution_md} />
            </details>
          )}
        </div>
      ) : (
        <div className="stack">
          <input value={editing} onChange={(e) => setEditing(e.target.value)} placeholder="正确答案" />
          <div className="row">
            <button className="primary" onClick={() => patch({ answer: editing })}>保存</button>
            <button onClick={() => setEditing(null)}>取消</button>
          </div>
        </div>
      )}

      {q.answer_source === "official" && v.agree === true && <div className="muted small">✓ AI 独立解出的答案一致</div>}
      {q.answer_source === "official" && v.agree === null && v.ai_answer !== undefined && (
        <details>
          <summary className="muted small">AI 也独立解了一遍（这类题没法自动比对，可以对照看看）</summary>
          <Md text={v.ai_answer || "（没有给出）"} />
          {v.ai_solution_md && <Md text={v.ai_solution_md} />}
        </details>
      )}
      {q.needs_review && (
        <div className="notice stack">
          <div>⚠ AI 独立解出的答案不一样：</div>
          <Md text={v.ai_answer || "（没有给出）"} />
          {v.ai_solution_md && (
            <details>
              <summary className="small">AI 的解答过程</summary>
              <Md text={v.ai_solution_md} />
            </details>
          )}
          <div className="small">通常是 AI 错了，也可能是答案页识别错了。对照上面的原题看一眼：</div>
          <div className="row">
            <button className="chip" onClick={() => patch({ reviewed: true })}>官方答案没问题</button>
            <button className="chip" onClick={() => setEditing(q.answer?.final ?? "")}>修改答案</button>
          </div>
        </div>
      )}
      {!q.needs_review && editing === null && (
        <div className="row">
          <button className="chip" onClick={() => setEditing(q.answer?.final ?? "")}>修改答案</button>
        </div>
      )}
      {error && <div className="error">{error}</div>}

      {q.stem_md && (
        <details>
          <summary className="muted small">识别出的题目文字</summary>
          <Md text={q.stem_md} />
          {q.options?.map((o) => <Md key={o.key} text={`${o.key}. ${o.md}`} />)}
          {q.sub_questions?.map((s) => <Md key={s.no} text={`${s.no} ${s.md}`} />)}
        </details>
      )}
    </div>
  );
}

export default function BankPaper() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<BankPaperInfo | null>(null);
  const [filter, setFilter] = useState<"all" | "review" | "noanswer">("all");
  const [jobId, setJobId] = useState<string | null>(params.get("job"));
  const [error, setError] = useState("");
  const cur = useCurriculum(paper?.subject);

  const load = useCallback(() => api.get<BankPaperInfo>(`/api/bank/papers/${id}`).then(setPaper), [id]);
  useEffect(() => {
    load();
  }, [load]);
  const job = useJob(jobId, () => {
    load();
    setJobId(null);
  });
  // 没有任务编号（比如从列表点进来）时，导入中的卷子定时刷新
  useEffect(() => {
    if (paper?.status !== "processing" || jobId) return;
    const t = window.setInterval(load, 3000);
    return () => window.clearInterval(t);
  }, [paper?.status, jobId, load]);

  const act = async (fn: () => Promise<unknown>) => {
    setError("");
    try {
      await fn();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (!paper) return <div className="muted">加载中…</div>;
  const st = paper.stats;
  const qs = paper.questions ?? [];
  const shown = qs.filter((q) => filter === "all" || (filter === "review" ? q.needs_review : !q.answer?.final || q.answer_source === "ai_unverified"));
  const kpName = (c: string) => cur?.names[c]?.split(" › ").pop() ?? c;
  const update = (nq: BankQuestion) => {
    setPaper((p) => p && { ...p, questions: (p.questions ?? []).map((q) => (q.id === nq.id ? nq : q)) });
    api.get<BankPaperInfo>(`/api/bank/papers/${id}`).then((p) => setPaper((old) => old && { ...old, stats: p.stats }));
  };

  return (
    <>
      <div className="topbar">
        <h1>{paper.title}</h1>
      </div>
      <div className="muted small" style={{ marginTop: -6, marginBottom: 10 }}>
        {paperMeta(paper)} · {paper.pages.length} 页（{paper.files.map((f) => f.name).filter(Boolean).join("、")}）
      </div>

      {(jobId || paper.status === "processing") && (
        <div className="card stack">
          {jobId ? <JobProgress job={job} /> : <div>正在导入…</div>}
          <p className="muted small" style={{ margin: 0 }}>可以先离开，导入完成后在"题库"里能看到。</p>
        </div>
      )}
      {paper.status === "failed" && <div className="error">导入失败：{paper.error}</div>}

      {paper.status === "ready" && (
        <>
          <div className="stat-grid" style={{ margin: "10px 0" }}>
            <div className="stat"><b>{st.questions ?? 0}</b><span className="muted">道题</span></div>
            <div className="stat"><b>{st.official ?? 0}</b><span className="muted">有官方答案</span></div>
            <div className="stat"><b>{st.to_review ?? 0}</b><span className="muted">待核对</span></div>
          </div>
          {!!st.matched_captured && (
            <div className="card">✅ 已经录入的 {st.matched_captured} 道错题在这套卷子里，已补上官方答案。</div>
          )}
          {paper.error && <div className="notice" style={{ marginBottom: 10 }}>{paper.error}</div>}
          {!!st.unmatched_answers?.length && (
            <div className="notice" style={{ marginBottom: 10 }}>
              答案里有第 {st.unmatched_answers.join("、")} 题，但卷子里没识别出这几道题。可以点下面"重新识别"再试一次。
            </div>
          )}
          {(st.verify_paused || !!st.unchecked) && (
            <div className="card row spread">
              <span className="small">{st.verify_paused ? "今天的 AI 费用到上限了，" : ""}还有 {st.unchecked} 题没核对</span>
              <button className="chip" onClick={() => act(async () => setJobId((await api.post<{ job_id: string }>(`/api/bank/papers/${paper.id}/verify`)).job_id))}>
                继续核对
              </button>
            </div>
          )}

          <div className="row" style={{ margin: "10px 0" }}>
            <button className={`chip ${filter === "all" ? "on" : ""}`} onClick={() => setFilter("all")}>全部 {qs.length}</button>
            <button className={`chip ${filter === "review" ? "on" : ""}`} onClick={() => setFilter("review")}>⚠ 待核对 {st.to_review ?? 0}</button>
            <button className={`chip ${filter === "noanswer" ? "on" : ""}`} onClick={() => setFilter("noanswer")}>
              没有官方答案 {(st.ai_only ?? 0) + (st.no_answer ?? 0)}
            </button>
          </div>
          {shown.map((q) => <QuestionCard key={q.id} q={q} kpName={kpName} onChange={update} />)}
          {!shown.length && <div className="card muted">这里没有题。</div>}
        </>
      )}

      {error && <div className="error">{error}</div>}
      {paper.status !== "processing" && !jobId && (
        <div className="row" style={{ marginTop: 14 }}>
          <ConfirmButton className="" style={{ flex: 1 }} prompt="改过的答案会丢失，再点一次确认"
            onConfirm={() => act(async () => setJobId((await api.post<{ job_id: string }>(`/api/bank/papers/${paper.id}/reimport`)).job_id))}>
            重新识别
          </ConfirmButton>
          <ConfirmButton style={{ flex: 1 }} prompt="再点一次，确认删除"
            onConfirm={() => act(async () => { await api.del(`/api/bank/papers/${paper.id}`); navigate("/bank"); })}>
            删除这套卷子
          </ConfirmButton>
        </div>
      )}
    </>
  );
}

import { PointerEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ANSWER_SOURCE, api, Candidate, Doc, GRADING, runtime, subjectName } from "../api";
import { CauseChips, ImageViewer, KpPicker, Md, useCurriculum } from "../components/common";

interface Choice {
  selected: boolean;
  kp_codes: string[];
  error_causes: string[];
  answer: string;
}

type Page = NonNullable<Doc["pages"]>[number];

function RegionPicker({ page, existing, onClose }: { page: Page; existing: number[][]; onClose: (added: boolean) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const [start, setStart] = useState<[number, number] | null>(null);
  const [rect, setRect] = useState<number[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const frac = (e: PointerEvent): [number, number] => {
    const r = box.current!.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))];
  };
  const down = (e: PointerEvent) => {
    (e.target as Element).setPointerCapture(e.pointerId);
    const p = frac(e);
    setStart(p);
    setRect([p[0], p[1], p[0], p[1]]);
  };
  const move = (e: PointerEvent) => {
    if (!start) return;
    const p = frac(e);
    setRect([Math.min(start[0], p[0]), Math.min(start[1], p[1]), Math.max(start[0], p[0]), Math.max(start[1], p[1])]);
  };
  const save = async () => {
    if (!rect) return;
    setBusy(true);
    setError("");
    try {
      await api.post(`/api/pages/${page.id}/regions`, {
        bbox: [rect[0] * page.cw, rect[1] * page.ch, rect[2] * page.cw, rect[3] * page.ch],
      });
      onClose(true);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  const pct = (r: number[]) => ({ left: `${r[0] * 100}%`, top: `${r[1] * 100}%`, width: `${(r[2] - r[0]) * 100}%`, height: `${(r[3] - r[1]) * 100}%` });

  return (
    <div className="modal-bg" onClick={() => onClose(false)}>
      <div className="modal stack" onClick={(e) => e.stopPropagation()}>
        <div className="row spread">
          <b>第 {page.page_no} 页：用手指拖出题目的范围</b>
          <button className="primary" disabled={!rect || busy || rect[2] - rect[0] < 0.02} onClick={save}>添加这道题</button>
        </div>
        <p className="muted small">虚线框是已经识别出的题。框的范围要包括题目下面的作答空白，打印时会原样保留。</p>
        {error && <div className="error">{error}</div>}
        <div ref={box} className="picker" onPointerDown={down} onPointerMove={move} onPointerUp={() => setStart(null)}>
          <img src={runtime.fileUrl(`/api/pages/${page.id}/image?kind=corrected`)} alt="" draggable={false} />
          {existing.map((b, i) => (
            <div key={i} className="rect existing" style={pct([b[0] / page.cw, b[1] / page.ch, b[2] / page.cw, b[3] / page.ch])} />
          ))}
          {rect && <div className="rect" style={pct(rect)} />}
        </div>
      </div>
    </div>
  );
}

export default function Confirm() {
  const { id } = useParams();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [items, setItems] = useState<Candidate[]>([]);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [kpFor, setKpFor] = useState<string | null>(null);
  const [regionPage, setRegionPage] = useState<Page | null>(null);
  const [viewPage, setViewPage] = useState<Page | null>(null);
  const [showOriginal, setShowOriginal] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<{ created: number; merged: number; solving: number } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const cur = useCurriculum(doc?.subject);

  const load = useCallback(async () => {
    const d = await api.get<Doc>(`/api/documents/${id}`);
    setDoc(d);
    if (d.status === "processing") return;
    const c = await api.get<{ items: Candidate[] }>(`/api/documents/${id}/candidates`);
    setItems(c.items);
    setChoices((prev) => {
      const next = { ...prev };
      for (const it of c.items) {
        next[it.instance_id] ??= {
          selected: it.status === "candidate" ? it.preselected : it.status === "confirmed",
          kp_codes: it.kp_codes,
          error_causes: it.cause_suggestions,
          answer: "",
        };
      }
      return next;
    });
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (doc?.status !== "processing") return;
    const t = window.setInterval(load, 2000);
    return () => window.clearInterval(t);
  }, [doc?.status, load]);

  const rejectMatch = async (qid: string) => {
    setError("");
    try {
      await api.post(`/api/questions/${qid}/bank-match`, { action: "reject" });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const set = (iid: string, patch: Partial<Choice>) => setChoices((c) => ({ ...c, [iid]: { ...c[iid], ...patch } }));
  const pending = items.filter((i) => i.status === "candidate");
  const selectedCount = pending.filter((i) => choices[i.instance_id]?.selected).length;

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await api.post<{ created: number; merged: number; solving: number }>(`/api/documents/${id}/confirm`, {
        items: pending.map((i) => {
          const c = choices[i.instance_id];
          return { instance_id: i.instance_id, selected: c.selected, kp_codes: c.kp_codes, error_causes: c.error_causes, answer: c.answer || null };
        }),
      });
      setResult(r);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!doc) return <div className="muted">加载中…</div>;
  const kpName = (c: string) => cur?.names[c]?.split(" › ").pop() ?? c;

  return (
    <>
      <div className="topbar">
        <h1>{doc.title || `${subjectName(doc.subject)}卷子`}</h1>
        <span className="muted small">{subjectName(doc.subject)} · {doc.pages?.length} 页</span>
      </div>

      {doc.status === "processing" && <div className="card">还在处理，请稍候…</div>}
      {doc.error && <div className="notice" style={{ marginBottom: 10 }}>{doc.error}</div>}
      {result && (
        <div className="card">
          ✅ 新增 {result.created} 道错题{result.merged ? `，合并 ${result.merged} 道重复的题` : ""}
          {result.solving ? `；${result.solving} 道题 AI 正在后台解答` : ""}。
          <div className="row" style={{ marginTop: 8 }}>
            <Link to="/mistakes" className="btn">去错题本</Link>
            <Link to={`/print?document=${doc.id}`} className="btn primary">打印擦除后的原卷</Link>
          </div>
        </div>
      )}

      <div className="row" style={{ margin: "8px 0" }}>
        {doc.pages?.map((p) => (
          <span key={p.id} className="row" style={{ gap: 4 }}>
            <button className="chip" onClick={() => setViewPage(p)}>
              第 {p.page_no} 页擦除图{p.erase_status === "failed" ? "（失败）" : ""}
            </button>
            <button className="chip" onClick={() => setRegionPage(p)}>＋ 手动框题</button>
          </span>
        ))}
      </div>

      {items.map((it) => {
        const c = choices[it.instance_id];
        if (!c) return null;
        const locked = it.status !== "candidate";
        const orig = showOriginal[it.instance_id];
        return (
          <div key={it.instance_id} className={`card ${c.selected ? "selected" : ""} ${locked && !c.selected ? "dim" : ""}`}>
            <div className="row spread">
              <label className="row" style={{ gap: 6 }}>
                <input type="checkbox" style={{ width: 22, height: 22 }} checked={c.selected} disabled={locked}
                  onChange={(e) => set(it.instance_id, { selected: e.target.checked })} />
                <b>第 {it.number_label || "?"} 题</b>
                <span className="muted small">第 {it.page_no} 页</span>
              </label>
              <span className="row" style={{ gap: 4 }}>
                {it.grading && it.grading !== "none" && <span className={`badge ${it.grading === "right" ? "" : "TO_REDO"}`}>{GRADING[it.grading]}{it.score ? ` ${it.score}` : ""}</span>}
                {locked && <span className="badge">{it.status === "confirmed" ? "已确认" : "未选"}</span>}
              </span>
            </div>
            <img className="crop" style={{ marginTop: 8 }} loading="lazy" alt=""
              src={runtime.fileUrl(`/api/instances/${it.instance_id}/image?kind=${orig ? "original" : "erased"}`)}
              onClick={() => setShowOriginal((s) => ({ ...s, [it.instance_id]: !orig }))} />
            <div className="muted small">点图片切换{orig ? "擦除后" : "原图"}</div>
            {it.bank && (
              <div className="row small" style={{ marginTop: 6 }}>
                <span>📚 题库里有这道题：<Link to={`/bank/${it.bank.paper_id}`}>{it.bank.paper_title}</Link> 第 {it.bank.number_label} 题</span>
                <button className="chip" onClick={() => rejectMatch(it.question.id)}>不是这道题</button>
              </div>
            )}
            {it.question.stem_md && (
              <details style={{ marginTop: 6 }}>
                <summary className="muted small">识别出的题目文字</summary>
                <Md text={it.question.stem_md} />
                {it.question.options?.map((o) => <Md key={o.key} text={`${o.key}. ${o.md}`} />)}
              </details>
            )}
            {!locked && c.selected && (
              <div className="stack" style={{ marginTop: 8 }}>
                <div className="row">
                  <span className="muted small">知识点</span>
                  {c.kp_codes.map((k) => <span key={k} className="chip on">{kpName(k)}</span>)}
                  <button className="chip" onClick={() => setKpFor(it.instance_id)}>{c.kp_codes.length ? "修改" : "＋ 选择"}</button>
                </div>
                {cur && (
                  <CauseChips causes={cur.error_causes} value={c.error_causes} suggested={it.cause_suggestions}
                    onChange={(v) => set(it.instance_id, { error_causes: v })} />
                )}
                {it.question.answer_source === "none" || !it.question.answer?.final ? (
                  <label className="field">正确答案（选填；不填的话由 AI 解答，标"待核"）
                    <input value={c.answer} onChange={(e) => set(it.instance_id, { answer: e.target.value })} placeholder="如：C；或 x=2" />
                  </label>
                ) : (
                  <div className="muted small">答案：{it.question.answer.final}（{ANSWER_SOURCE[it.question.answer_source]}）</div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {error && <div className="error">{error}</div>}
      {!!pending.length && (
        <button className="primary block" style={{ position: "sticky", bottom: 80, marginTop: 12 }} disabled={busy} onClick={submit}>
          {busy ? "提交中…" : `确认 ${selectedCount} 道错题`}
        </button>
      )}

      {kpFor && doc && (
        <KpPicker subject={doc.subject} value={choices[kpFor].kp_codes}
          onClose={(v) => { if (v) set(kpFor, { kp_codes: v }); setKpFor(null); }} />
      )}
      {viewPage && (
        <ImageViewer title={`第 ${viewPage.page_no} 页 · 擦除后`} onClose={() => setViewPage(null)}
          src={runtime.fileUrl(`/api/pages/${viewPage.id}/image?kind=erased&max_side=2400`)} />
      )}
      {regionPage && (
        <RegionPicker page={regionPage} existing={items.filter((i) => i.page_no === regionPage.page_no).map((i) => i.bbox)}
          onClose={(added) => { setRegionPage(null); if (added) load(); }} />
      )}
    </>
  );
}

import { ChangeEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, BankPaperInfo, EXAM_KINDS, runtime, Subject, subjectName, SUBJECTS } from "../api";
import { fmtTime } from "../components/common";
import { DISTRICTS } from "./Onboarding";

const PAPER_STATUS: Record<string, [string, string]> = {
  processing: ["导入中", ""], ready: ["", ""], failed: ["导入失败", "warn"],
};

export function regionName(code: string | null): string {
  if (!code) return "";
  if (code === "beijing") return "北京";
  return DISTRICTS.find(([v]) => v === code)?.[1] ?? code;
}

export function paperMeta(p: BankPaperInfo): string {
  return [p.year, regionName(p.region), p.exam_kind_name, subjectName(p.subject)].filter(Boolean).join(" · ");
}

function ImportForm({ onCancel }: { onCancel: () => void }) {
  const navigate = useNavigate();
  const [subject, setSubject] = useState<Subject>("math");
  const [kind, setKind] = useState("yimo");
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [region, setRegion] = useState("haidian");
  const [title, setTitle] = useState("");
  const [papers, setPapers] = useState<File[]>([]);
  const [answers, setAnswers] = useState<File[]>([]);
  const [verify, setVerify] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const kindName = EXAM_KINDS.find(([v]) => v === kind)?.[1] ?? "";
  const auto = `${year ? `${year} ` : ""}${regionName(region)}${kindName} · ${subjectName(subject)}`;
  const pick = (set: (f: File[]) => void) => (e: ChangeEvent<HTMLInputElement>) => {
    set(Array.from(e.target.files ?? []));
  };

  const submit = async () => {
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("subject", subject);
    form.append("exam_kind", kind);
    form.append("year", year);
    form.append("region", region);
    form.append("title", title.trim() || auto);
    form.append("verify", verify ? "true" : "false");
    papers.forEach((f) => form.append("paper_files", f, f.name));
    answers.forEach((f) => form.append("answer_files", f, f.name));
    try {
      const r = await api.upload<{ paper_id: string; job_id: string }>("/api/bank/papers", form);
      navigate(`/bank/${r.paper_id}?job=${r.job_id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <div className="card stack">
      <div className="row spread">
        <h2 style={{ margin: 0 }}>导入一套卷子</h2>
        <button className="chip" onClick={onCancel}>取消</button>
      </div>
      {runtime.demo && <div className="notice">预览版不能上传导入，可以先看看表单；题库里已经有一套导入好的示例卷子。</div>}
      <div className="seg">
        {SUBJECTS.map((s) => (
          <button key={s.code} className={subject === s.code ? "on" : ""} onClick={() => setSubject(s.code)}>{s.name}</button>
        ))}
      </div>
      <div className="row">
        <label className="field" style={{ flex: 1 }}>年份
          <input inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value.replace(/\D/g, "").slice(0, 4))} />
        </label>
        <label className="field" style={{ flex: 1 }}>地区
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            <option value="beijing">北京（全市）</option>
            {DISTRICTS.filter(([v]) => v !== "other").map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        </label>
        <label className="field" style={{ flex: 1 }}>考试
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {EXAM_KINDS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        </label>
      </div>
      <label className="field">名称（不填就用"{auto}"）
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={auto} />
      </label>
      <label className="field">试卷：PDF，或者每页一张照片（可多选）
        <input type="file" accept="application/pdf,image/*" multiple onChange={pick(setPapers)} />
      </label>
      <label className="field">答案及评分标准（选填；如果答案就在试卷 PDF 的最后几页，这里不用传）
        <input type="file" accept="application/pdf,image/*" multiple onChange={pick(setAnswers)} />
      </label>
      <label className="row small" style={{ flexWrap: "nowrap", alignItems: "flex-start" }}>
        <input type="checkbox" checked={verify} onChange={(e) => setVerify(e.target.checked)} style={{ width: "auto", flex: "none" }} />
        <span style={{ flex: 1, minWidth: 0 }}>AI 独立解一遍，和官方答案对不上的标出来请你看一眼（每题约 1–2 分钱）</span>
      </label>
      <p className="muted small">
        导入大约每页半分钟：拆页、切题、按题号对答案、分类知识点。卷子只存在你的私有数据仓库里。
      </p>
      {error && <div className="error">{error}</div>}
      <button className="primary block" disabled={!papers.length || busy} onClick={submit}>
        {busy ? "上传中…" : `开始导入（${papers.length + answers.length} 个文件）`}
      </button>
    </div>
  );
}

export default function Bank() {
  const [papers, setPapers] = useState<BankPaperInfo[] | null>(null);
  const [subject, setSubject] = useState("");
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    api.get<BankPaperInfo[]>(`/api/bank/papers${subject ? `?subject=${subject}` : ""}`).then(setPapers);
  }, [subject]);

  const total = papers?.reduce((n, p) => n + (p.stats.questions ?? 0), 0) ?? 0;

  return (
    <>
      <div className="topbar">
        <h1>题库</h1>
        {!importing && <button className="primary" onClick={() => setImporting(true)}>＋ 导入卷子</button>}
      </div>
      {importing && <ImportForm onCancel={() => setImporting(false)} />}

      <div className="row" style={{ margin: "10px 0" }}>
        <button className={`chip ${!subject ? "on" : ""}`} onClick={() => setSubject("")}>全部</button>
        {SUBJECTS.map((s) => (
          <button key={s.code} className={`chip ${subject === s.code ? "on" : ""}`} onClick={() => setSubject(s.code)}>{s.name}</button>
        ))}
        {!!papers?.length && <span className="muted small">{papers.length} 套 · {total} 题</span>}
      </div>

      {papers === null && <div className="muted">加载中…</div>}
      {papers?.length === 0 && !importing && (
        <div className="card stack">
          <b>还没有卷子</b>
          <p className="muted small" style={{ margin: 0 }}>
            题库收北京的真题、各区一模二模和区统考（期中、期末），最好连同"答案及评分标准"一起导入。
            之后拍照录入错题时，如果这道题在题库里，会直接带上官方答案和出处，不用再等 AI 解答。
          </p>
          <button className="primary" onClick={() => setImporting(true)}>导入第一套卷子</button>
        </div>
      )}
      {papers?.map((p) => {
        const [label, cls] = PAPER_STATUS[p.status] ?? [p.status, ""];
        return (
          <Link key={p.id} to={`/bank/${p.id}`} className="card" style={{ display: "block", color: "inherit" }}>
            <div className="row spread">
              <b>{p.title}</b>
              {label && <span className={`badge ${cls}`}>{label}</span>}
            </div>
            <div className="muted small">{paperMeta(p)} · 导入于 {fmtTime(p.created_at).slice(0, 10)}</div>
            {p.status === "ready" && (
              <div className="row small" style={{ marginTop: 6, gap: 6 }}>
                <span>{p.stats.questions ?? 0} 题</span>
                <span className="muted">官方答案 {p.stats.official ?? 0}</span>
                {!!p.stats.to_review && <span className="badge warn">⚠ {p.stats.to_review} 题待核对</span>}
                {!!p.stats.unchecked && <span className="badge">{p.stats.unchecked} 题未核对</span>}
              </div>
            )}
          </Link>
        );
      })}
    </>
  );
}

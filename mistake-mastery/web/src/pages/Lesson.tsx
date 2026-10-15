import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, KnowledgeDetail, KpLesson, LessonRef, LessonState, runtime, subjectName } from "../api";
import { JobProgress, Md, useJob, useStudent } from "../components/common";

const day = (iso: string) => iso.slice(0, 10);

function RefChips({ refs, map }: { refs: string[]; map: Record<string, LessonRef> }) {
  const known = refs.map((r) => map[r]).filter(Boolean);
  if (!known.length) return null;
  return (
    <div className="row lesson-refs">
      {known.map((r) => (
        <Link key={r.id} className="chip" to={r.kind === "mistake" ? `/mistakes/${r.id}` : `/bank/${r.paper_id}`}>
          {r.kind === "mistake" ? "错题" : "真题"} · {r.label}
        </Link>
      ))}
    </div>
  );
}

/** 讲解正文：一句话、要点、方法、易错点、例题、自查。 */
export function LessonBody({ lesson }: { lesson: KpLesson }) {
  const ex = lesson.example;
  return (
    <div className="lesson">
      {lesson.one_line && <div className="lesson-lead"><Md text={lesson.one_line} /></div>}
      {!!lesson.key_points.length && (
        <section>
          <h3>要点</h3>
          <ol>
            {lesson.key_points.map((k, i) => (
              <li key={i}>{k.title && <b>{k.title}</b>}<Md text={k.md} /></li>
            ))}
          </ol>
        </section>
      )}
      {!!lesson.method.length && (
        <section>
          <h3>遇到这类题，这样想</h3>
          <ol className="lesson-steps">{lesson.method.map((m, i) => <li key={i}><Md text={m} /></li>)}</ol>
        </section>
      )}
      {!!lesson.pitfalls.length && (
        <section>
          <h3>你容易错在这里</h3>
          {lesson.pitfalls.map((p, i) => (
            <div key={i} className="lesson-pitfall">
              {p.title && <b>⚠ {p.title}</b>}
              <Md text={p.md} />
              <RefChips refs={p.refs} map={lesson.refs} />
            </div>
          ))}
        </section>
      )}
      {ex && (
        <section>
          <h3>例题</h3>
          {ex.ref && <RefChips refs={[ex.ref]} map={lesson.refs} />}
          <div className="lesson-q"><Md text={ex.question_md} /></div>
          <div className="lesson-a"><Md text={ex.steps_md} /></div>
          {ex.answer && <div className="lesson-ans"><b>答案：</b><Md text={ex.answer} /></div>}
        </section>
      )}
      {!!lesson.self_check.length && (
        <section>
          <h3>做题时提醒自己</h3>
          <ul className="lesson-checks">{lesson.self_check.map((c, i) => <li key={i}><Md text={c} /></li>)}</ul>
        </section>
      )}
    </div>
  );
}

/** 知识点详情页上的讲解卡片：生成、进度、正文、重新生成。 */
export function LessonCard({ code, weak }: { code: string; weak: boolean }) {
  const { student } = useStudent();
  const url = `/api/knowledge/${code}/lesson`;
  const [state, setState] = useState<LessonState | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = () =>
    api.get<LessonState>(`${url}?student_id=${student.id}`).then((d) => {
      setState(d);
      setJobId(d.job?.id ?? null);
    }).catch((e) => setError(e.message));
  useEffect(() => {
    setState(null);
    setError("");
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, student.id]);

  const job = useJob(jobId, (j) => {
    if (j.status === "done") load();
    else setError(j.error || "生成失败");
  });
  const start = (fresh: boolean) => {
    setError("");
    api.post<{ job_id: string }>(url, { student_id: student.id, fresh })
      .then((r) => setJobId(r.job_id)).catch((e) => setError(e.message));
  };
  const busy = !!jobId && job?.status !== "failed" && job?.status !== "done";
  const lesson = state?.lesson;

  return (
    <div className="card">
      <div className="row spread">
        <h2 style={{ margin: 0 }}>📖 讲解</h2>
        {lesson && !busy && <span className="muted small">AI 写的 · 请对照课本</span>}
      </div>
      {!state && !error && <div className="muted small">加载中…</div>}
      {busy && <div style={{ marginTop: 8 }}><JobProgress job={job} /></div>}
      {error && (
        <div style={{ marginTop: 8 }}>
          <div className="error">{error}</div>
          <button style={{ marginTop: 6 }} onClick={() => start(!!lesson)}>再试一次</button>
        </div>
      )}
      {state && !lesson && !busy && !error && (
        <div className="stack" style={{ marginTop: 8 }}>
          <div className="muted small">
            让 AI 按{student.name}在这个知识点上的错题写一份讲解：要点、解题方法、{student.name}自己容易错的地方、一道例题。
            {weak ? "这是薄弱知识点，建议先看讲解再重做错题。" : ""}
          </div>
          <button className="primary" onClick={() => start(false)}>生成讲解（约半分钟）</button>
        </div>
      )}
      {lesson && !busy && (
        <>
          {lesson.new_mistakes > 0 && (
            <div className="banner">
              写完讲解后又录入了 {lesson.new_mistakes} 道这个知识点的错题。
              <button className="chip" onClick={() => start(true)}>重新生成</button>
            </div>
          )}
          <LessonBody lesson={lesson} />
          <div className="row spread" style={{ marginTop: 10 }}>
            <span className="muted small">{day(lesson.created_at)} 写的</span>
            <span className="row" style={{ gap: 6 }}>
              <Link to={`/knowledge/${code}/lesson`} className="chip btn">{runtime.demo ? "单独看" : "🖨 打印 / 单独看"}</Link>
              <button className="chip" onClick={() => start(true)}>重新生成</button>
            </span>
          </div>
        </>
      )}
    </div>
  );
}

/** 单独一页的讲解：给孩子在平板上看，或者打印出来。 */
export default function LessonPage() {
  const { code } = useParams();
  const { student } = useStudent();
  const [kp, setKp] = useState<KnowledgeDetail | null>(null);
  const [state, setState] = useState<LessonState | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<KnowledgeDetail>(`/api/knowledge/${code}?student_id=${student.id}`).then(setKp).catch((e) => setError(e.message));
    api.get<LessonState>(`/api/knowledge/${code}/lesson?student_id=${student.id}`).then(setState).catch((e) => setError(e.message));
  }, [code, student.id]);

  if (error) return <div className="error">{error}</div>;
  if (!kp || !state) return <div className="muted">加载中…</div>;
  const lesson = state.lesson;
  const open = kp.mistake_list.filter((m) => m.status !== "MASTERED");
  return (
    <>
      <div className="topbar">
        <h1>{kp.name}</h1>
        {lesson && !runtime.demo && <button className="chip no-print" onClick={() => window.print()}>🖨 打印</button>}
      </div>
      <div className="muted small" style={{ marginTop: -6, marginBottom: 10 }}>
        {subjectName(kp.subject)} · {kp.path.split(" › ").slice(0, -1).join(" › ")} · {student.name}
        {lesson ? ` · ${day(lesson.created_at)} · AI 讲解，请对照课本` : ""}
      </div>
      {lesson ? <div className="card lesson-page"><LessonBody lesson={lesson} /></div> : (
        <div className="card muted">还没有讲解。<Link to={`/knowledge/${code}`}>回到知识点</Link>生成一份。</div>
      )}
      <div className="row no-print" style={{ margin: "10px 0" }}>
        <Link to={`/knowledge/${code}`} className="btn" style={{ flex: 1 }}>‹ 回到知识点</Link>
        {!!open.length && (
          <Link to={`/print?mistakes=${open.map((m) => m.id).join(",")}`} className="btn primary" style={{ flex: 1 }}>
            看完重做 {open.length} 道错题
          </Link>
        )}
      </div>
    </>
  );
}

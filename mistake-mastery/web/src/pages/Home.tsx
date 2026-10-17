import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, BlindSpot, subjectName, SyncStatus } from "../api";
import { fmtTime, useStudent } from "../components/common";
import { BlindSpotRow } from "./Knowledge";

interface Today {
  counts: Record<string, number>;
  pending_documents: { id: string; title: string | null; subject: string; status: string; created_at: string }[];
  recent_prints: { id: string; title: string | null; status: string; created_at: string }[];
  exams: { name: string; exam_date: string }[];
  status_names: Record<string, string>;
  sync: SyncStatus;
}

const DOC_STATUS: Record<string, string> = { processing: "处理中", ready: "待确认", failed: "处理失败" };

function daysUntil(date: string): number {
  return Math.ceil((new Date(date + "T00:00:00").getTime() - Date.now()) / 86400000);
}

export function SyncChip({ sync }: { sync: SyncStatus }) {
  if (!sync.is_git_repo) return <span className="badge warn">未连接数据仓库</span>;
  if (sync.last_error) return <span className="badge warn">同步待重试</span>;
  if (sync.dirty || sync.unpushed_commits) return <span className="badge">待同步</span>;
  return <span className="badge MASTERED">已同步</span>;
}

export default function Home() {
  const { student, students, setStudentId } = useStudent();
  const [data, setData] = useState<Today | null>(null);
  const [spots, setSpots] = useState<BlindSpot[]>([]);

  useEffect(() => {
    setData(null);
    setSpots([]);
    api.get<Today>(`/api/today?student_id=${student.id}`).then(setData);
    api.get<BlindSpot[]>(`/api/knowledge/blind-spots?student_id=${student.id}&limit=3`).then(setSpots).catch(() => setSpots([]));
  }, [student.id]);

  const c = data?.counts ?? {};
  const open = (c.TO_REDO ?? 0) + (c.TO_TUTOR ?? 0) + (c.TO_VARIANT ?? 0) + (c.TO_REVIEW ?? 0) + (c.STUBBORN ?? 0);
  const nextExam = data?.exams.find((e) => daysUntil(e.exam_date) >= 0);

  return (
    <>
      <div className="topbar">
        <h1>{student.name} · 今日</h1>
        <div className="row">
          {data && <SyncChip sync={data.sync} />}
          {students.length > 1 && (
            <select value={student.id} onChange={(e) => setStudentId(e.target.value)} style={{ width: "auto" }}>
              {students.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          )}
        </div>
      </div>

      {nextExam && (
        <div className="card">
          📅 距 <b>{nextExam.name}</b> 还有 <b>{daysUntil(nextExam.exam_date)}</b> 天
        </div>
      )}

      <div className="stat-grid" style={{ margin: "10px 0" }}>
        <Link to="/mistakes?status=TO_REDO" className="stat"><b>{c.TO_REDO ?? 0}</b><span className="muted">待重做</span></Link>
        <Link to="/mistakes" className="stat"><b>{open}</b><span className="muted">未学透</span></Link>
        <Link to="/mistakes?status=MASTERED" className="stat"><b>{c.MASTERED ?? 0}</b><span className="muted">已学透</span></Link>
      </div>

      <div className="row" style={{ marginBottom: 10 }}>
        <Link to="/capture" className="btn primary" style={{ flex: 1 }}>📷 拍照录入</Link>
        <Link to="/print" className="btn" style={{ flex: 1 }}>🖨 打印重做</Link>
      </div>

      {!!spots.length && (
        <div className="card">
          <div className="row spread">
            <h2 style={{ margin: 0 }}>掌握死角</h2>
            <Link to="/knowledge" className="small">全部知识点 ›</Link>
          </div>
          {spots.map((b) => <BlindSpotRow key={b.code} b={b} showSubject />)}
        </div>
      )}

      {!!data?.pending_documents.length && (
        <div className="card">
          <h2>待处理的卷子</h2>
          {data.pending_documents.map((d) => (
            <Link key={d.id} to={`/documents/${d.id}`} className="row spread" style={{ padding: "6px 0" }}>
              <span>{d.title || subjectName(d.subject)} <span className="muted small">{fmtTime(d.created_at)}</span></span>
              <span className={`badge ${d.status === "ready" ? "TO_REDO" : d.status === "failed" ? "warn" : ""}`}>
                {DOC_STATUS[d.status] ?? d.status}
              </span>
            </Link>
          ))}
        </div>
      )}

      {!!data?.recent_prints.length && (
        <div className="card">
          <h2>最近打印</h2>
          {data.recent_prints.map((p) => (
            <Link key={p.id} to={`/p/${p.id}`} className="row spread" style={{ padding: "6px 0" }}>
              <span>{p.title}</span>
              <span className="muted small">{fmtTime(p.created_at)}</span>
            </Link>
          ))}
        </div>
      )}

      {data && !open && !data.pending_documents.length && (
        <div className="card muted">还没有错题。卷子发回来后，点"拍照录入"开始吧。</div>
      )}
    </>
  );
}

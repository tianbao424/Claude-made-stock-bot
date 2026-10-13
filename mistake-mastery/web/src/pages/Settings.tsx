import { useEffect, useState } from "react";
import { api, SyncStatus } from "../api";
import { fmtTime, useStudent } from "../components/common";
import { SyncChip } from "./Home";
import { DISTRICTS, TEXTBOOKS } from "./Onboarding";

interface AppSettings {
  models: Record<string, string>;
  eraser: string;
  erasers: string[];
  keys: Record<string, boolean>;
  spent_today: number;
  daily_cap: number;
}
interface Exam {
  id: string;
  name: string;
  kind: string;
  exam_date: string;
}

const TASK_NAMES: Record<string, string> = { recognize: "识别切题", classify: "知识点分类", solve: "解答", verify: "交叉校验（v0.2）", tutor: "讲解（v0.3）" };
const ERASER_NAMES: Record<string, string> = { local_color: "本地（只擦彩色笔迹）", baidu: "百度", youdao: "有道", textin: "TextIn", none: "不擦除" };

export default function Settings() {
  const { student, reload } = useStudent();
  const [name, setName] = useState(student.name);
  const [district, setDistrict] = useState(student.district ?? "");
  const [books, setBooks] = useState<Record<string, string>>(student.textbooks ?? {});
  const [exams, setExams] = useState<Exam[]>([]);
  const [examName, setExamName] = useState("");
  const [examDate, setExamDate] = useState("");
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [msg, setMsg] = useState("");

  const loadExams = () => api.get<Exam[]>(`/api/students/${student.id}/exams`).then(setExams);
  useEffect(() => {
    loadExams();
    api.get<AppSettings>("/api/settings").then(setSettings);
    api.get<SyncStatus>("/api/sync/status").then(setSync);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [student.id]);

  const saveStudent = async () => {
    await api.patch(`/api/students/${student.id}`, { name, district: district || null, textbooks: books });
    await reload();
    setMsg("已保存");
  };
  const syncNow = async () => {
    setSyncing(true);
    try {
      const r = await api.post<{ status: SyncStatus }>("/api/sync");
      setSync(r.status);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <>
      <div className="topbar"><h1>我的</h1></div>

      <div className="card stack">
        <h2>孩子档案</h2>
        <label className="field">称呼<input value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="field">所在区
          <select value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">不填</option>
            {DISTRICTS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        </label>
        <div className="row">
          {(["math", "physics"] as const).map((s) => (
            <label key={s} className="field" style={{ flex: 1 }}>{s === "math" ? "数学" : "物理"}教材
              <select value={books[s] ?? "rjb"} onChange={(e) => setBooks({ ...books, [s]: e.target.value })}>
                {TEXTBOOKS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
              </select>
            </label>
          ))}
        </div>
        <button className="primary" onClick={saveStudent}>保存</button>
        {msg && <span className="muted small">{msg}</span>}
      </div>

      <div className="card stack">
        <h2>考试日历</h2>
        {exams.map((e) => (
          <div key={e.id} className="row spread">
            <span>{e.name} · {e.exam_date}</span>
            <button className="chip" onClick={() => api.del(`/api/exams/${e.id}`).then(loadExams)}>删除</button>
          </div>
        ))}
        <div className="row">
          <input style={{ flex: 2 }} placeholder="如：期末" value={examName} onChange={(e) => setExamName(e.target.value)} />
          <input style={{ flex: 2 }} type="date" value={examDate} onChange={(e) => setExamDate(e.target.value)} />
          <button disabled={!examName || !examDate}
            onClick={() => api.post(`/api/students/${student.id}/exams`, { name: examName, exam_date: examDate }).then(() => { setExamName(""); setExamDate(""); loadExams(); })}>
            添加
          </button>
        </div>
      </div>

      <div className="card stack">
        <div className="row spread">
          <h2 style={{ margin: 0 }}>GitHub 数据同步</h2>
          {sync && <SyncChip sync={sync} />}
        </div>
        {sync && !sync.is_git_repo && (
          <div className="notice">数据目录还不是 git 仓库。按 README 的步骤 clone 你的私有数据仓库，并在 .env 里设置 XT_DATA_DIR。</div>
        )}
        {sync?.is_git_repo && (
          <div className="muted small">
            最后同步：{fmtTime(sync.last_synced_at) || "本次启动后还没同步"}；最后推送：{fmtTime(sync.last_pushed_at) || "—"}
            {sync.unpushed_commits ? `；${sync.unpushed_commits} 个提交待推送` : ""}
          </div>
        )}
        {sync?.last_error && <div className="error">{sync.last_error}</div>}
        <button disabled={syncing || !sync?.is_git_repo} onClick={syncNow}>{syncing ? "同步中…" : "立即同步"}</button>
      </div>

      {settings && (
        <div className="card stack">
          <h2>AI 与擦除</h2>
          <div className="muted small">今天 AI 费用约 ¥{settings.spent_today.toFixed(2)}，每日上限 ¥{settings.daily_cap}</div>
          <label className="field">去手写接口
            <select value={settings.eraser} onChange={(e) => api.patch<AppSettings>("/api/settings", { eraser: e.target.value }).then(setSettings)}>
              {settings.erasers.map((x) => (
                <option key={x} value={x}>{ERASER_NAMES[x] ?? x}{x in settings.keys && !settings.keys[x] ? "（未配置密钥）" : ""}</option>
              ))}
            </select>
          </label>
          {Object.entries(settings.models).map(([task, spec]) => (
            <label key={task} className="field">{TASK_NAMES[task] ?? task}（平台:模型名）
              <input defaultValue={spec} onBlur={(e) => e.target.value !== spec &&
                api.patch<AppSettings>("/api/settings", { models: { [task]: e.target.value } }).then(setSettings)} />
            </label>
          ))}
          <div className="muted small">
            已配置密钥：{Object.entries(settings.keys).filter(([, v]) => v).map(([k]) => k).join("、") || "无"}。密钥在电脑上的 .env 文件里配置。
          </div>
        </div>
      )}

      <div className="card stack">
        <h2>账号</h2>
        <div className="row">
          <button onClick={() => api.post("/api/logout").then(() => (location.href = "/login"))}>退出登录</button>
          <button className="danger" onClick={() => confirm("所有设备都需要重新输入密码，确定吗？") &&
            api.post("/api/logout-all").then(() => (location.href = "/login"))}>退出所有设备</button>
        </div>
      </div>
    </>
  );
}

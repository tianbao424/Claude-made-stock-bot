import { useCallback, useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, Student } from "./api";
import { StudentContext } from "./components/common";
import Bank from "./pages/Bank";
import BankPaper from "./pages/BankPaper";
import Capture from "./pages/Capture";
import Confirm from "./pages/Confirm";
import Home from "./pages/Home";
import Knowledge from "./pages/Knowledge";
import KnowledgeDetail from "./pages/KnowledgeDetail";
import Login from "./pages/Login";
import MistakeDetail from "./pages/MistakeDetail";
import Mistakes from "./pages/Mistakes";
import Onboarding from "./pages/Onboarding";
import Print from "./pages/Print";
import PrintJobPage from "./pages/PrintJob";
import Settings from "./pages/Settings";

const STUDENT_KEY = "xt.student";

function Nav() {
  const { pathname } = useLocation();
  return (
    <nav className="nav">
      <NavLink to="/" end>
        <span className="ico">🏠</span>今日
      </NavLink>
      <NavLink to="/mistakes" className={({ isActive }) => (isActive || pathname.startsWith("/knowledge") ? "active" : "")}>
        <span className="ico">📚</span>错题本
      </NavLink>
      <NavLink to="/capture" className="plus">
        <span className="ico">＋</span>拍照
      </NavLink>
      <NavLink to="/print">
        <span className="ico">🖨</span>打印
      </NavLink>
      <NavLink to="/settings">
        <span className="ico">⚙️</span>我的
      </NavLink>
    </nav>
  );
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [students, setStudents] = useState<Student[]>([]);
  const [studentId, setStudentIdState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STUDENT_KEY);
    } catch {
      return null;
    }
  });

  const reload = useCallback(async () => {
    setStudents(await api.get<Student[]>("/api/students"));
  }, []);

  useEffect(() => {
    if (location.pathname === "/login") {
      setReady(true);
      return;
    }
    (async () => {
      const s = await api.get<{ logged_in: boolean }>("/api/session");
      if (!s.logged_in) {
        navigate(`/login?next=${encodeURIComponent(location.pathname + location.search)}`, { replace: true });
        setReady(true);
        return;
      }
      await reload();
      setReady(true);
    })().catch(() => setReady(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname === "/login"]);

  const setStudentId = (id: string) => {
    setStudentIdState(id);
    try {
      localStorage.setItem(STUDENT_KEY, id);
    } catch {
      /* 隐私模式下存不了，只是下次要重新选 */
    }
  };

  if (location.pathname === "/login") return <Login />;
  if (!ready) return <div className="app muted">加载中…</div>;
  if (!students.length) return <Onboarding onCreated={reload} />;
  const student = students.find((s) => s.id === studentId) ?? students[0];

  return (
    <StudentContext.Provider value={{ student, students, setStudentId, reload }}>
      <div className="app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/capture" element={<Capture />} />
          <Route path="/documents/:id" element={<Confirm />} />
          <Route path="/mistakes" element={<Mistakes />} />
          <Route path="/mistakes/:id" element={<MistakeDetail />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/knowledge/:code" element={<KnowledgeDetail />} />
          <Route path="/print" element={<Print />} />
          <Route path="/p/:id" element={<PrintJobPage />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/bank" element={<Bank />} />
          <Route path="/bank/:id" element={<BankPaper />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </div>
      <Nav />
    </StudentContext.Provider>
  );
}

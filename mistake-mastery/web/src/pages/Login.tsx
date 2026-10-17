import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

export default function Login() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [configured, setConfigured] = useState(true);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    api.get<{ logged_in: boolean; password_configured: boolean }>("/api/session").then((s) => {
      setConfigured(s.password_configured);
      if (s.logged_in) navigate(params.get("next") || "/", { replace: true });
    });
  }, [navigate, params]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/api/login", { password });
      navigate(params.get("next") || "/", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app" style={{ paddingTop: "18vh" }}>
      <h1 style={{ fontSize: 28, margin: 0 }}>学透</h1>
      <p className="muted">错一题，透一类。</p>
      {!configured && (
        <div className="notice">还没有设置家庭密码：在电脑上的 .env 文件里填写 XT_FAMILY_PASSWORD，然后重启程序。</div>
      )}
      <form onSubmit={submit} className="stack" style={{ marginTop: 24 }}>
        <input type="password" autoComplete="current-password" placeholder="家庭密码" value={password}
          onChange={(e) => setPassword(e.target.value)} autoFocus />
        {error && <div className="error">{error}</div>}
        <button className="primary block" disabled={busy || !password}>
          {busy ? "登录中…" : "登录"}
        </button>
      </form>
    </div>
  );
}

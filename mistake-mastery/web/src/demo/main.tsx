// 预览版入口：同一套页面，后端换成浏览器里的模拟（见 mock.ts），打包成一个文件发给家人先看看。
import "katex/dist/katex.min.css";
import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { Link, MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { runtime } from "../api";
import App from "../App";
import "../styles.css";
import "./demo.css";
import { Fixtures, installMockApi, MockServer } from "./mock";

function dataUrlToFile(url: string, name: string): File {
  const [head, b64] = url.split(",");
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return new File([bytes], name, { type: head.slice(5).split(";")[0] });
}

const TOUR: { to: string; title: string; text: string }[] = [
  { to: "/capture", title: "① 拍照录入", text: "点「用示例照片」，再点上传：矫正、切题、识别、擦除笔迹" },
  { to: "/", title: "② 确认错题", text: "处理完会自动打开；勾选错题，看擦除前后，改知识点和错因" },
  { to: "/print", title: "⑤ 打印", text: "错题重做单或原卷还原，看生成的 A4 页面" },
  { to: "", title: "⑥ 回填", text: "孩子做完，在打印单页面逐题记 ✓ ✗，状态跟着变" },
  { to: "/mistakes", title: "错题本", text: "每道题的三道关、错题旅程、答案" },
];

function DemoBar({ server, printId, onReset }: { server: MockServer; printId: string; onReset: () => void }) {
  const [open, setOpen] = useState(true);
  const [armed, setArmed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const reset = () => {
    if (!armed) {
      setArmed(true);
      window.setTimeout(() => setArmed(false), 4000);
      return;
    }
    setArmed(false);
    server.reset();
    onReset();
    navigate("/");
  };
  return (
    <div className="demo-bar">
      <div className="demo-bar-inner">
        <div className="demo-head">
          <span className="demo-tag">预览版</span>
          <span className="demo-note">
            {location.pathname === "/login" ? "随便输入一个密码就能登录" : "示例数据 · AI 和擦除结果是事先生成的 · 改动只留在这个页面里"}
          </span>
          <button className="chip" onClick={() => setOpen(!open)}>{open ? "收起导览" : "导览"}</button>
        </div>
        {open && (
          <div className="demo-tour">
            <ol>
              {TOUR.map((t) => (
                <li key={t.title}>
                  <Link to={t.to || `/p/${printId}`} onClick={() => setOpen(false)}>
                    <b>{t.title}</b>
                    <span>{t.text}</span>
                  </Link>
                </li>
              ))}
            </ol>
            <div className="demo-foot">
              <span>③ 举一反三（5 道变式）和 ④ AI 分步讲解在 v0.2、v0.3 开发，预览版里还没有。</span>
              <button className={`chip ${armed ? "armed" : ""}`} onClick={reset}>{armed ? "再点一次，确认重置" : "重置示例数据"}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DemoRoot({ server, printId }: { server: MockServer; printId: string }) {
  const [gen, setGen] = useState(0);
  return (
    <MemoryRouter>
      <DemoBar server={server} printId={printId} onReset={() => setGen((g) => g + 1)} />
      <App key={gen} />
    </MemoryRouter>
  );
}

const fx = JSON.parse(document.getElementById("xt-fixtures")!.textContent!) as Fixtures;
const server = installMockApi(fx);
runtime.demo = true;
runtime.fileUrl = (path) => server.fileUrl(path);
runtime.pdfPages = (id) => server.pdfPages(id);
runtime.sampleFiles = async () => [dataUrlToFile(server.samplePhoto(), "示例-数学期中-第1页.jpg")];

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <DemoRoot server={server} printId={fx.initial.print_jobs[0].id} />
  </React.StrictMode>,
);

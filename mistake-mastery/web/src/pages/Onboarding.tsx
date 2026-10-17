import { FormEvent, useState } from "react";
import { api } from "../api";

const DISTRICTS = [
  ["haidian", "海淀"], ["xicheng", "西城"], ["dongcheng", "东城"], ["chaoyang", "朝阳"], ["fengtai", "丰台"],
  ["shijingshan", "石景山"], ["tongzhou", "通州"], ["changping", "昌平"], ["daxing", "大兴"], ["shunyi", "顺义"],
  ["fangshan", "房山"], ["mentougou", "门头沟"], ["pinggu", "平谷"], ["huairou", "怀柔"], ["miyun", "密云"],
  ["yanqing", "延庆"], ["other", "其他"],
];
export const TEXTBOOKS = [
  ["rjb", "人教版"], ["bjb", "北京版"], ["bsd", "北师大版"],
];
export { DISTRICTS };

export default function Onboarding({ onCreated }: { onCreated: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [district, setDistrict] = useState("");
  const [math, setMath] = useState("rjb");
  const [physics, setPhysics] = useState("rjb");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/api/students", { name, grade: 9, district: district || null, textbooks: { math, physics } });
      await onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="app">
      <div className="topbar">
        <h1>先建一个孩子档案</h1>
      </div>
      <p className="muted">这些信息只存在你的私有数据仓库里，用来预填教材版本和考试日历。称呼用昵称就行。</p>
      <form onSubmit={submit} className="card stack">
        <label className="field">称呼
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：小雨" />
        </label>
        <label className="field">所在区（选填）
          <select value={district} onChange={(e) => setDistrict(e.target.value)}>
            <option value="">不填</option>
            {DISTRICTS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
          </select>
        </label>
        <div className="row">
          <label className="field" style={{ flex: 1 }}>数学教材
            <select value={math} onChange={(e) => setMath(e.target.value)}>
              {TEXTBOOKS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </select>
          </label>
          <label className="field" style={{ flex: 1 }}>物理教材
            <select value={physics} onChange={(e) => setPhysics(e.target.value)}>
              {TEXTBOOKS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </select>
          </label>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="primary block" disabled={!name.trim()}>开始使用</button>
      </form>
    </div>
  );
}

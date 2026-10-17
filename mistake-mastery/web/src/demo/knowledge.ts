// 预览版的知识点整理：按 app/services/knowledge.py 的同一套规则（docs/06 §6），用页面上当前的错题现算。
import type { BankPaperInfo, BlindSpot, Curriculum, KnowledgeNode, KpNode, MasteryLevel, MistakeDetail, Subject } from "../api";

const TAU_DAYS = 21;
const ALPHA = 2;
const SECONDARY = 0.5;
const RESULT_SCORE: Record<string, number> = { correct: 1, partial: 0.5, wrong: 0 };
const WEAK = 0.4;
const GOOD = 0.7;
const FREQUENT = 0.6;
const OPEN = new Set(["TO_REDO", "TO_TUTOR", "TO_VARIANT", "TO_REVIEW", "STUBBORN"]);

interface Stat {
  sw: number;
  swr: number;
  observations: number;
  mistakes: Set<string>;
  open: Set<string>;
  mastered: Set<string>;
  stubborn: Set<string>;
  repeat: Set<string>;
  causes: Map<string, number>;
  last_wrong_at: string | null;
}

const mastery = (x: Stat | undefined) => (x && x.observations ? (x.swr + ALPHA * 0.5) / (x.sw + ALPHA) : null);
const levelOf = (s: number | null): MasteryLevel => (s === null ? "none" : s < WEAK ? "weak" : s <= GOOD ? "medium" : "good");

export class KnowledgeIndex {
  parent: Record<string, string | null> = {};
  node: Record<string, KpNode> = {};
  subjectOf: Record<string, Subject> = {};
  children: Record<string, string[]> = {};

  constructor(private cur: Record<string, Curriculum>, private weights: Record<string, number | null>) {
    for (const [subject, c] of Object.entries(cur)) {
      const walk = (n: KpNode, parent: string | null) => {
        this.parent[n.code] = parent;
        this.node[n.code] = n;
        this.subjectOf[n.code] = subject as Subject;
        this.children[n.code] = n.children.map((ch) => ch.code);
        n.children.forEach((ch) => walk(ch, n.code));
      };
      c.tree.forEach((n) => walk(n, null));
    }
  }

  private ancestors(code: string): string[] {
    const out: string[] = [];
    for (let c: string | null = code; c && c in this.node; c = this.parent[c]) out.push(c);
    return out;
  }

  private isLeaf = (code: string) => !this.children[code]?.length;
  weight = (code: string) => this.weights[code] ?? null;
  path = (code: string) => this.cur[this.subjectOf[code]]?.names[code] ?? code;

  compute(mistakes: MistakeDetail[], subject: string): Record<string, Stat> {
    const stats: Record<string, Stat> = {};
    const st = (c: string) => (stats[c] ??= {
      sw: 0, swr: 0, observations: 0, mistakes: new Set(), open: new Set(), mastered: new Set(), stubborn: new Set(),
      repeat: new Set(), causes: new Map(), last_wrong_at: null,
    });
    const now = Date.now();
    for (const m of mistakes.filter((x) => x.subject === subject)) {
      const w: Record<string, number> = {};
      m.kp_codes.forEach((code, i) => {
        for (const n of this.ancestors(code)) w[n] = Math.max(w[n] ?? 0, i === 0 ? 1 : SECONDARY);
      });
      const d = 0.8 + 0.1 * (m.difficulty ?? 3);
      for (const [n, c] of Object.entries(w)) {
        const x = st(n);
        x.mistakes.add(m.id);
        if (OPEN.has(m.status)) x.open.add(m.id);
        if (m.status === "MASTERED") x.mastered.add(m.id);
        if (m.status === "STUBBORN") x.stubborn.add(m.id);
        if (m.wrong_count >= 2 || m.round > 1) x.repeat.add(m.id);
        for (const cause of m.error_causes) x.causes.set(cause, (x.causes.get(cause) ?? 0) + 1);
        if (!x.last_wrong_at || m.last_wrong_at > x.last_wrong_at) x.last_wrong_at = m.last_wrong_at;
        for (const a of m.attempts) {
          const r = RESULT_SCORE[a.result];
          if (r === undefined) continue;
          const age = Math.max(0, (now - new Date(a.created_at).getTime()) / 86400000);
          const wt = c * d * Math.exp(-age / TAU_DAYS);
          x.sw += wt;
          x.swr += wt * r;
          x.observations += 1;
        }
      }
    }
    return stats;
  }

  bankCounts(bank: Record<string, BankPaperInfo>): Record<string, number> {
    const out: Record<string, number> = {};
    for (const p of Object.values(bank)) {
      for (const q of p.questions ?? []) {
        if (q.kp_codes[0]) for (const n of this.ancestors(q.kp_codes[0])) out[n] = (out[n] ?? 0) + 1;
      }
    }
    return out;
  }

  nodeJson(code: string, x: Stat | undefined, bank: Record<string, number>): KnowledgeNode {
    const s = mastery(x);
    return {
      code, name: this.node[code].name, level: this.node[code].level, weight: this.weight(code),
      mastery: s === null ? null : Math.round(s * 1000) / 1000, status: levelOf(s),
      observations: x?.observations ?? 0, mistakes: x?.mistakes.size ?? 0, open: x?.open.size ?? 0,
      mastered: x?.mastered.size ?? 0, stubborn: x?.stubborn.size ?? 0, repeat: x?.repeat.size ?? 0,
      bank: bank[code] ?? 0, last_wrong_at: x?.last_wrong_at ?? null,
    };
  }

  blindSpots(subject: Subject, stats: Record<string, Stat>, bank: Record<string, number>, limit = 8): BlindSpot[] {
    const causeNames = Object.fromEntries(this.cur[subject].error_causes.map((c) => [c.code, c.name]));
    const out: BlindSpot[] = [];
    for (const [code, x] of Object.entries(stats)) {
      if (!this.isLeaf(code)) continue;
      const s = mastery(x);
      if (!x.open.size && (s === null || s >= WEAK)) continue;
      const weight = this.weight(code) ?? 0.5;
      const risk = (x.open.size + 2 * x.stubborn.size + x.repeat.size + 3 * (1 - (s ?? 0.5))) * (0.6 + weight);
      const reasons: string[] = [];
      if (x.open.size) reasons.push(`${x.open.size} 道未学透`);
      if (x.stubborn.size) reasons.push(`${x.stubborn.size} 道顽固错题`);
      if (x.repeat.size) reasons.push(`${x.repeat.size} 道反复错`);
      if (s !== null && s < WEAK) reasons.push("最近做得不好");
      if (weight >= FREQUENT) reasons.push("中考常考");
      const top = [...x.causes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([c]) => c).filter((c) => causeNames[c]);
      if (top.length) reasons.push("主要错因：" + top.map((c) => causeNames[c]).join("、"));
      out.push({ ...this.nodeJson(code, x, bank), subject, path: this.path(code), risk: Math.round(risk * 100) / 100, reasons });
    }
    return out.sort((a, b) => b.risk - a.risk || a.code.localeCompare(b.code)).slice(0, limit);
  }

  overview(mistakes: MistakeDetail[], bankPapers: Record<string, BankPaperInfo>, subject: Subject) {
    const stats = this.compute(mistakes, subject);
    const bank = this.bankCounts(bankPapers);
    const codes = Object.keys(this.node).filter((c) => this.subjectOf[c] === subject);
    const leaves = Object.keys(stats).filter(this.isLeaf);
    const levels = leaves.map((c) => levelOf(mastery(stats[c])));
    const roots = Object.keys(stats).filter((c) => !this.parent[c]);
    const union = (k: "open" | "mastered") => new Set(roots.flatMap((c) => [...stats[c][k]])).size;
    const build = (code: string): KnowledgeNode => ({ ...this.nodeJson(code, stats[code], bank), children: this.children[code].map(build) });
    return {
      subject,
      summary: {
        points: leaves.length, weak: levels.filter((l) => l === "weak").length,
        medium: levels.filter((l) => l === "medium").length, good: levels.filter((l) => l === "good").length,
        open: union("open"), mastered: union("mastered"),
      },
      blind_spots: this.blindSpots(subject, stats, bank),
      untouched: codes
        .filter((c) => this.isLeaf(c) && !stats[c] && (this.weight(c) ?? 0) >= FREQUENT)
        .map((c) => ({ code: c, name: this.node[c].name, path: this.path(c), weight: this.weight(c), bank: bank[c] ?? 0 }))
        .sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0) || b.bank - a.bank || a.code.localeCompare(b.code))
        .slice(0, 10),
      tree: this.cur[subject].tree.map((n) => build(n.code)),
    };
  }

  topBlindSpots(mistakes: MistakeDetail[], bankPapers: Record<string, BankPaperInfo>, limit: number): BlindSpot[] {
    const bank = this.bankCounts(bankPapers);
    return (["math", "physics"] as Subject[])
      .flatMap((s) => this.blindSpots(s, this.compute(mistakes, s), bank, limit))
      .sort((a, b) => b.risk - a.risk)
      .slice(0, Math.max(1, Math.min(limit, 20)));
  }

  detail(code: string, mistakes: MistakeDetail[], bankPapers: Record<string, BankPaperInfo>) {
    const subject = this.subjectOf[code];
    const stats = this.compute(mistakes, subject);
    const bank = this.bankCounts(bankPapers);
    const x = stats[code];
    const causeNames = Object.fromEntries(this.cur[subject].error_causes.map((c) => [c.code, c.name]));
    const order: Record<string, number> = { STUBBORN: 0, TO_REDO: 1, TO_TUTOR: 1, TO_VARIANT: 2, TO_REVIEW: 3, MASTERED: 4 };
    const list = mistakes
      .filter((m) => x?.mistakes.has(m.id))
      .sort((a, b) => (order[a.status] ?? 5) - (order[b.status] ?? 5) || b.last_wrong_at.localeCompare(a.last_wrong_at));
    const done = new Set(mistakes.map((m) => m.bank?.question_id).filter(Boolean));
    const inKp = (c: string) => c === code || c.startsWith(code + ".");
    const bankQuestions = Object.values(bankPapers)
      .flatMap((p) => (p.questions ?? []).filter((q) => q.kp_codes.some(inKp)).map((q) => ({
        id: q.id, paper_id: p.id, paper_title: p.title, number_label: q.number_label, primary: inKp(q.kp_codes[0]),
        done: done.has(q.id), year: p.year ?? 0, seq: q.seq,
      })))
      .sort((a, b) => Number(a.done) - Number(b.done) || Number(b.primary) - Number(a.primary) || b.year - a.year || a.seq - b.seq)
      .slice(0, 20)
      .map(({ year: _y, seq: _s, ...rest }) => rest);
    return {
      list,
      body: {
        ...this.nodeJson(code, x, bank), subject, path: this.path(code),
        causes: x ? [...x.causes.entries()].sort((a, b) => b[1] - a[1]).map(([c, n]) => ({ code: c, name: causeNames[c] ?? c, n })) : [],
        children: this.children[code].map((c) => this.nodeJson(c, stats[c], bank)),
        bank_questions: bankQuestions,
      },
    };
  }
}

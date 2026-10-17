// 预览版的"后端"：在浏览器里用示例数据模拟 /api/* 接口。
// 示例数据由 web/demo/make_fixtures.py 用真实后端生成（AI 部分是固定的模拟结果），
// 这里只负责记住页面上的操作，并按 v0.1 的规则更新错题状态。
import { EXAM_KINDS } from "../api";
import type { BankPaperInfo, BankQuestion, BlindSpot, Candidate, Curriculum, Doc, KpLesson, MistakeDetail, PrintJobInfo, Student, Subject, SyncStatus } from "../api";
import { KnowledgeIndex } from "./knowledge";

interface Exam {
  id: string;
  name: string;
  kind: string;
  exam_date: string;
  subjects: string[];
}

export interface Fixtures {
  images: Record<string, string>;
  pdf: Record<string, string[]>;
  student_id: string;
  math_doc: string;
  phys_doc: string;
  initial: {
    students: Student[];
    exams: Exam[];
    documents: Record<string, Doc>;
    candidates: Record<string, { document: Doc; items: Candidate[] }>;
    mistakes: MistakeDetail[];
    print_jobs: PrintJobInfo[];
    settings: { models: Record<string, string>; eraser: string } & Record<string, unknown>;
    sync: SyncStatus;
    bank: Record<string, BankPaperInfo>;
  };
  curriculum: Record<string, Curriculum>;
  kp_weights: Record<string, number | null>; // 每个知识点的中考权重（继承自所在模块）
  lessons: Record<string, { lesson: KpLesson; mistake_ids: string[] }>; // 示例讲解（用真实后端生成，AI 部分是写好的）
  math_after_confirm: Record<string, MistakeDetail>;
  redo_order: string[]; // 错题重做单 PDF 按这个顺序排题（每种组合都事先生成好了）
}

interface FakeJob {
  id: string;
  kind: string;
  start: number;
  ms: number;
  stages: string[];
  result: Record<string, unknown>;
  done: boolean;
  onDone?: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Body = Record<string, any>;

class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const STATUS_NAMES: Record<string, string> = {
  TO_REDO: "待重做", TO_TUTOR: "待讲解", TO_VARIANT: "待变式", TO_REVIEW: "待复习", MASTERED: "已学透", STUBBORN: "顽固错题",
};
const SUBJECT_NAMES: Record<string, string> = { math: "数学", physics: "物理" };

const now = () => new Date().toISOString().slice(0, 19) + "+00:00";
let seq = 0;
const uid = () => `demo-${Date.now().toString(36)}-${(++seq).toString(36)}`;
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));

export class MockServer {
  private fx: Fixtures;
  loggedIn = true;
  private students: Student[] = [];
  private exams: Exam[] = [];
  private docs: Record<string, Doc> = {};
  private visibleDocs = new Set<string>();
  private cands: Record<string, Candidate[]> = {};
  private mistakes: MistakeDetail[] = [];
  private prints: PrintJobInfo[] = [];
  private printPages: Record<string, string[]> = {};
  private jobs: Record<string, FakeJob> = {};
  private settings!: Fixtures["initial"]["settings"];
  private bank: Record<string, BankPaperInfo> = {};
  private sync!: SyncStatus;
  private syncTimer: number | undefined;
  private kp: KnowledgeIndex;
  private lessons: Record<string, KpLesson> = {};
  private lessonJobs: Record<string, string> = {}; // 知识点 → 正在生成的任务

  constructor(fx: Fixtures) {
    this.fx = fx;
    this.kp = new KnowledgeIndex(fx.curriculum, fx.kp_weights ?? {});
    this.reset();
  }

  reset() {
    const ini = clone(this.fx.initial);
    this.loggedIn = true;
    this.students = ini.students;
    this.exams = ini.exams;
    this.docs = ini.documents;
    this.visibleDocs = new Set([this.fx.phys_doc]); // 数学卷要"拍照录入"之后才出现
    this.cands = Object.fromEntries(Object.entries(ini.candidates).map(([k, v]) => [k, v.items]));
    this.mistakes = ini.mistakes;
    this.prints = ini.print_jobs;
    this.printPages = Object.fromEntries(this.prints.map((p) => [p.id, this.fx.pdf[p.id] ?? []]));
    this.jobs = {};
    this.settings = ini.settings;
    this.sync = ini.sync;
    this.bank = ini.bank ?? {};
    this.lessons = {};
    this.lessonJobs = {};
  }

  private markLessons(spots: BlindSpot[]): BlindSpot[] {
    return spots.map((b) => ({ ...b, lesson: b.code in this.lessons }));
  }

  private lessonState(code: string) {
    const l = this.lessons[code];
    const basis = new Set(this.fx.lessons?.[code]?.mistake_ids ?? []);
    const mine = this.mistakes.filter((m) => m.kp_codes.some((c) => c === code || c.startsWith(code + ".")));
    const jobId = this.lessonJobs[code];
    const job = jobId && !this.jobs[jobId]?.done ? { id: jobId, status: "running" } : null;
    return { lesson: l ? { ...l, new_mistakes: mine.filter((m) => !basis.has(m.id)).length } : null, job };
  }

  // ------------------------------------------------------------ 图片和 PDF

  fileUrl(path: string): string {
    const bq = path.match(/^\/api\/bank\/questions\/([^/]+)\/image/);
    if (bq) return this.fx.images[`bankq:${bq[1]}`] ?? "";
    const m = path.match(/^\/api\/(instances|pages)\/([^/]+)\/image\?(.*)$/);
    if (!m) return path;
    const kind = new URLSearchParams(m[3]).get("kind") ?? "erased";
    return this.fx.images[`${m[1] === "pages" ? "page" : "inst"}:${m[2]}:${kind}`] ?? "";
  }

  pdfPages(printJobId: string): string[] {
    return this.printPages[printJobId] ?? [];
  }

  samplePhoto(): string {
    return this.fx.images["photo:math"] ?? this.fx.images[`page:${this.docs[this.fx.math_doc].pages![0].id}:corrected`];
  }

  // ------------------------------------------------------------ 后台任务（按时间推进）

  private submit(kind: string, ms: number, stages: string[], result: Record<string, unknown>, onDone?: () => void) {
    const job: FakeJob = { id: uid(), kind, start: Date.now(), ms, stages, result, done: false, onDone };
    this.jobs[job.id] = job;
    return job.id;
  }

  private tick() {
    for (const j of Object.values(this.jobs)) {
      if (!j.done && Date.now() - j.start >= j.ms) {
        j.done = true;
        j.onDone?.();
      }
    }
  }

  private jobJson(j: FakeJob) {
    if (j.done) return { id: j.id, kind: j.kind, status: "done", progress: { stage: "完成", pct: 100 }, result: j.result, error: null };
    const t = (Date.now() - j.start) / j.ms;
    const stage = j.stages[Math.min(j.stages.length - 1, Math.floor(t * j.stages.length))];
    return { id: j.id, kind: j.kind, status: "running", progress: { stage, pct: Math.round(t * 100) }, result: null, error: null };
  }

  // 改了数据以后，几秒钟后"推送到 GitHub"
  private touch() {
    this.sync = { ...this.sync, dirty: true };
    window.clearTimeout(this.syncTimer);
    this.syncTimer = window.setTimeout(() => {
      this.sync = { ...this.sync, dirty: false, unpushed_commits: 0, last_synced_at: now(), last_pushed_at: now() };
    }, 4000);
  }

  // ------------------------------------------------------------ 错题

  private summary(m: MistakeDetail) {
    const { question: _q, instances: _i, attempts: _a, ...rest } = m;
    return rest;
  }

  private mistake(id: string) {
    const m = this.mistakes.find((x) => x.id === id);
    if (!m) throw new HttpError(404, "找不到这道错题");
    return m;
  }

  private kpNames(subject: string, codes: string[]) {
    const names = this.fx.curriculum[subject]?.names ?? {};
    return codes.map((c) => names[c] ?? c);
  }

  private setStatus(m: MistakeDetail, status: string) {
    m.status = status;
    m.status_name = STATUS_NAMES[status];
  }

  // 重做原题的结果，规则同 app/services/mastery.py（REDO_RESULT）
  private recordResult(m: MistakeDetail, result: string, context: string) {
    if (!["correct", "wrong", "partial"].includes(result)) throw new HttpError(400, "result 只能是 correct / wrong / partial");
    m.attempts.push({ id: uid(), round: m.round, context, result, graded_by: "guardian", error_cause: null, note: null, created_at: now() });
    const g = m.gates;
    if (m.status === "TO_REVIEW" || m.status === "MASTERED") {
      if (result !== "correct") {
        // 回炉：轮次 +1，三道关重置
        m.round += 1;
        m.wrong_count += 1;
        m.gates = { original: false, variant: false, spaced: false };
        m.next_review_at = null;
        m.last_wrong_at = now();
        this.setStatus(m, "TO_REDO");
      }
      return;
    }
    if (result === "correct") {
      if (m.status === "TO_REDO" || m.status === "TO_TUTOR") {
        m.gates = { ...g, original: true };
        this.setStatus(m, "TO_VARIANT");
      }
      return;
    }
    m.gates = { ...g, original: false };
    m.wrong_count += 1;
    m.last_wrong_at = now();
    this.setStatus(m, "TO_TUTOR");
  }

  private fromCandidate(doc: Doc, it: Candidate, choice: Body): MistakeDetail {
    const q = it.question;
    const kp = choice.kp_codes?.length ? choice.kp_codes : it.kp_codes;
    const causes: string[] = choice.error_causes ?? it.cause_suggestions;
    const t = now();
    return {
      id: uid(), status: "TO_REDO", status_name: STATUS_NAMES.TO_REDO, round: 1, wrong_count: 1,
      gates: { original: false, variant: false, spaced: false }, error_causes: causes,
      subject: doc.subject, question_type: q.type, stem_md: q.stem_md, answer_source: q.answer_source,
      bj_slot: q.bj_slot, difficulty: q.difficulty, kp_codes: kp, kp_names: this.kpNames(doc.subject, kp),
      instance_id: it.instance_id, number_label: it.number_label,
      document: { id: doc.id, title: doc.title, source_kind: doc.source_kind, exam_date: doc.exam_date },
      last_wrong_at: t, created_at: t, next_review_at: null, bank: it.bank ?? null,
      explain: null, explain_job: null, kp_lessons: [],
      question: { id: q.id, stem_md: q.stem_md, options: q.options, sub_questions: q.sub_questions, answer: q.answer,
        solution_md: null, answer_source: q.answer_source, verification: null },
      instances: [{ id: it.instance_id, page_id: doc.pages![0].id, number_label: it.number_label,
        student_answer: it.student_answer, grading: it.grading, score: it.score }],
      attempts: [{ id: uid(), round: 1, context: "capture", result: it.grading === "partial" ? "partial" : "wrong",
        graded_by: "teacher", error_cause: causes[0] ?? null, note: null, created_at: t }],
    };
  }

  private bankStats(paper: BankPaperInfo) {
    const qs: BankQuestion[] = paper.questions ?? [];
    paper.stats = {
      ...paper.stats,
      official: qs.filter((x) => ["official", "manual"].includes(x.answer_source)).length,
      to_review: qs.filter((x) => x.needs_review).length,
    };
  }

  // ------------------------------------------------------------ 打印

  private printJson(p: PrintJobInfo, withItems: boolean) {
    const { items, ...rest } = p;
    if (!withItems) return rest;
    return {
      ...rest,
      items: (items ?? []).map((it) => {
        const m = it.mistake_id ? this.mistakes.find((x) => x.id === it.mistake_id) : undefined;
        return { ...it, status: m?.status ?? null, status_name: m?.status_name ?? null };
      }),
    };
  }

  // 预览版的 PDF 是事先用真实后端生成好的：所选错题的每种组合各一份，最后一页是答案页
  private renderPages(template: string, docId: string | null, mistakes: MistakeDetail[], withKey: boolean) {
    if (template === "page_restore") {
      const pages = this.fx.pdf[`sample:page_restore:${docId}`] ?? [];
      return { pages, count: pages.length };
    }
    const all = this.fx.pdf[`redo:${mistakes.map((m) => m.instance_id).sort().join(",")}`] ?? [];
    const body = all.slice(0, -1);
    return { pages: withKey ? all : body, count: body.length };
  }

  // ------------------------------------------------------------ 路由

  handle(method: string, url: URL, body: Body | FormData | null): unknown {
    this.tick();
    const p = url.pathname;
    const q = url.searchParams;
    const b = (body instanceof FormData ? {} : body ?? {}) as Body;
    const route = (pattern: RegExp) => p.match(pattern);
    let m: RegExpMatchArray | null;

    // 登录
    if (p === "/api/health") return { ok: true };
    if (p === "/api/session") return { logged_in: this.loggedIn, password_configured: true };
    if (p === "/api/login") {
      if (!b.password) throw new HttpError(400, "请输入密码");
      this.loggedIn = true;
      return { ok: true };
    }
    if (p === "/api/logout" || p === "/api/logout-all") {
      this.loggedIn = false;
      return { ok: true };
    }

    // 孩子、考试、字典、设置、同步
    if (p === "/api/students" && method === "GET") return this.students;
    if (p === "/api/students" && method === "POST") {
      const s: Student = { id: uid(), name: b.name, grade: 9, district: b.district ?? null, textbooks: b.textbooks ?? {}, settings: {} };
      this.students.push(s);
      this.touch();
      return s;
    }
    if ((m = route(/^\/api\/students\/([^/]+)$/)) && method === "PATCH") {
      const s = this.students.find((x) => x.id === m![1]);
      if (!s) throw new HttpError(404, "找不到孩子档案");
      Object.assign(s, { name: b.name ?? s.name, district: b.district ?? null, textbooks: b.textbooks ?? s.textbooks });
      this.touch();
      return s;
    }
    if ((m = route(/^\/api\/students\/([^/]+)\/exams$/))) {
      if (method === "POST") {
        this.exams.push({ id: uid(), name: b.name, kind: b.kind ?? "other", exam_date: b.exam_date, subjects: ["math", "physics"] });
        this.touch();
      }
      return [...this.exams].sort((x, y) => x.exam_date.localeCompare(y.exam_date));
    }
    if ((m = route(/^\/api\/exams\/([^/]+)$/)) && method === "DELETE") {
      this.exams = this.exams.filter((e) => e.id !== m![1]);
      this.touch();
      return { ok: true };
    }
    if ((m = route(/^\/api\/curriculum\/([^/]+)$/))) {
      const c = this.fx.curriculum[m[1]];
      if (!c) throw new HttpError(404, "没有这个学科");
      return c;
    }
    if (p === "/api/settings") {
      if (method === "PATCH") {
        if (b.eraser) this.settings.eraser = b.eraser;
        if (b.models) this.settings.models = { ...this.settings.models, ...b.models };
      }
      return this.settings;
    }
    if (p === "/api/sync/status") return this.sync;
    if (p === "/api/sync") {
      this.sync = { ...this.sync, dirty: false, unpushed_commits: 0, last_synced_at: now(), last_pushed_at: now() };
      return { status: this.sync };
    }
    if ((m = route(/^\/api\/jobs\/([^/]+)$/))) {
      const j = this.jobs[m[1]];
      if (!j) throw new HttpError(404, "找不到任务");
      return this.jobJson(j);
    }
    if (p === "/api/today") {
      const counts: Record<string, number> = {};
      for (const x of this.mistakes) counts[x.status] = (counts[x.status] ?? 0) + 1;
      const docs = [...this.visibleDocs].map((id) => this.docs[id]);
      return {
        counts,
        pending_documents: docs.filter((d) => ["processing", "ready", "failed"].includes(d.status))
          .sort((x, y) => y.created_at.localeCompare(x.created_at))
          .map((d) => ({ id: d.id, title: d.title, subject: d.subject, status: d.status, created_at: d.created_at })),
        recent_prints: [...this.prints].sort((x, y) => y.created_at.localeCompare(x.created_at)).slice(0, 5)
          .map((x) => ({ id: x.id, title: x.title, status: x.status, created_at: x.created_at })),
        exams: [...this.exams].sort((x, y) => x.exam_date.localeCompare(y.exam_date)).map((e) => ({ name: e.name, exam_date: e.exam_date })),
        status_names: STATUS_NAMES,
        sync: this.sync,
      };
    }

    // 拍照录入
    if (p === "/api/captures") {
      const form = body as FormData;
      if (!form.getAll("files").length) throw new HttpError(400, "请至少选一张照片");
      const id = this.fx.math_doc;
      if (this.visibleDocs.has(id)) {
        throw new HttpError(400, "预览版只带了一份示例卷子，已经录入过了。可以在首页或错题本里继续看；点顶部「重置示例数据」可以从头再来。");
      }
      const doc = this.docs[id];
      const title = String(form.get("title") ?? "").trim();
      if (title) doc.title = title;
      doc.status = "processing";
      doc.created_at = now();
      this.visibleDocs.add(id);
      this.touch();
      const job = this.submit("capture", 6000, ["矫正页面", "识别切题", "擦除笔迹", "知识点分类"], { document_id: id }, () => {
        doc.status = "ready";
      });
      return { document_id: id, job_id: job };
    }
    if (p === "/api/documents") {
      return [...this.visibleDocs].map((id) => this.docs[id]).sort((x, y) => y.created_at.localeCompare(x.created_at));
    }
    if ((m = route(/^\/api\/documents\/([^/]+)(\/candidates|\/confirm)?$/))) {
      const doc = this.docs[m[1]];
      if (!doc || !this.visibleDocs.has(doc.id)) throw new HttpError(404, "找不到这份卷子");
      if (!m[2]) return doc;
      const items = this.cands[doc.id];
      if (m[2] === "/candidates") return { document: doc, items };
      let created = 0;
      let solving = 0;
      for (const choice of (b.items ?? []) as Body[]) {
        const it = items.find((x) => x.instance_id === choice.instance_id);
        if (!it || it.status !== "candidate") continue;
        if (!choice.selected) {
          it.status = "discarded";
          continue;
        }
        it.status = "confirmed";
        const ready = this.fx.math_after_confirm[it.instance_id];
        const mk = ready ? clone(ready) : this.fromCandidate(doc, it, choice);
        if (!it.bank && mk.bank) {
          mk.bank = null;
          mk.answer_source = mk.question.answer_source = "ai_unverified";
        }
        mk.id = uid();
        mk.created_at = mk.last_wrong_at = now();
        if (choice.kp_codes?.length) {
          mk.kp_codes = choice.kp_codes;
          mk.kp_names = this.kpNames(doc.subject, choice.kp_codes);
        }
        if (choice.error_causes) mk.error_causes = choice.error_causes;
        if (choice.answer) {
          mk.question.answer = { final: choice.answer };
          mk.question.solution_md = null;
          mk.answer_source = mk.question.answer_source = "manual";
        } else if (it.question.answer_source === "none" && mk.answer_source.startsWith("ai")) {
          solving += 1;
        }
        this.mistakes.unshift(mk);
        created += 1;
      }
      doc.status = "confirmed";
      this.touch();
      return { created, merged: 0, solving };
    }
    if (route(/^\/api\/pages\/[^/]+\/erase$/) && method === "POST") {
      return { ok: true }; // 预览版的擦除图是事先生成好的
    }
    if (route(/^\/api\/pages\/[^/]+\/regions$/)) {
      throw new HttpError(400, "预览版不能手动框题。正式版里在这里拖出题目范围，就会新增一道题。");
    }

    // 题库（预览版不能上传新卷子，里面放了一套事先导入好的示例卷子）
    if (p === "/api/bank/papers" && method === "POST") {
      throw new HttpError(400, "预览版不能上传导入。题库里已经放了一套用真实流程导入的示例卷子，可以点开看看；正式版在这里上传 PDF，每页约半分钟。");
    }
    if (p === "/api/bank/papers") {
      const subject = q.get("subject");
      return Object.values(this.bank).filter((x) => !subject || x.subject === subject)
        .map(({ questions: _q, ...rest }) => rest);
    }
    if ((m = route(/^\/api\/bank\/papers\/([^/]+)(\/verify|\/reimport)?$/))) {
      const paper = this.bank[m[1]];
      if (!paper) throw new HttpError(404, "找不到这套卷子");
      if (m[2]) throw new HttpError(400, "预览版不能重新识别或核对。");
      if (method === "DELETE") {
        delete this.bank[paper.id];
        this.touch();
        return { ok: true };
      }
      if (method === "PATCH") {
        if (typeof b.title === "string" && b.title.trim()) paper.title = b.title.trim().slice(0, 100);
        if (typeof b.year === "number") paper.year = b.year || null;
        if (typeof b.region === "string") paper.region = b.region || null;
        if (typeof b.exam_kind === "string") {
          paper.exam_kind = b.exam_kind;
          paper.exam_kind_name = EXAM_KINDS.find(([v]) => v === b.exam_kind)?.[1] ?? b.exam_kind;
        }
        if (b.subject === "math" || b.subject === "physics") {
          paper.subject = b.subject;
          for (const bq of paper.questions ?? []) {
            bq.kp_codes = [];
            bq.bj_slot = null;
          }
        }
        this.touch();
        return { ...paper, job_id: null };
      }
      return paper;
    }
    if ((m = route(/^\/api\/bank\/questions\/([^/]+)$/)) && method === "PATCH") {
      const paper = Object.values(this.bank).find((x) => x.questions?.some((y) => y.id === m![1]));
      const bq = paper?.questions?.find((y) => y.id === m![1]);
      if (!paper || !bq) throw new HttpError(404, "找不到题目");
      if (typeof b.answer === "string") {
        bq.answer = b.answer.trim() ? { final: b.answer.trim() } : null;
        bq.answer_source = b.answer.trim() ? "manual" : "none";
      }
      if (b.reviewed !== undefined || typeof b.answer === "string") {
        bq.verification = { ...(bq.verification ?? {}), reviewed: true };
      }
      bq.needs_review = bq.answer_source === "official" && bq.verification?.agree === false && !bq.verification?.reviewed;
      this.bankStats(paper);
      this.touch();
      return bq;
    }
    if ((m = route(/^\/api\/questions\/([^/]+)\/bank-match$/))) {
      // "不是这道题"：取消匹配，答案交给 AI（预览版直接用事先生成的 AI 答案）
      const qid = m[1];
      for (const items of Object.values(this.cands)) {
        for (const it of items) {
          if (it.question.id !== qid || !it.bank) continue;
          it.bank = null;
          if (it.question.answer_source === "official") {
            it.question.answer = null;
            it.question.answer_source = "none";
          }
        }
      }
      for (const mk of this.mistakes) {
        if (mk.question.id !== qid) continue;
        mk.bank = null;
        if (mk.answer_source === "official") mk.answer_source = mk.question.answer_source = "ai_unverified";
      }
      this.touch();
      return { ok: true, solving: false };
    }

    // 知识点整理
    if (p === "/api/knowledge") {
      const subject = q.get("subject") as Subject;
      if (!this.fx.curriculum[subject]) throw new HttpError(400, "不支持的学科");
      const o = this.kp.overview(this.mistakes, this.bank, subject);
      return { ...o, blind_spots: this.markLessons(o.blind_spots) };
    }
    if (p === "/api/knowledge/blind-spots") return this.markLessons(this.kp.topBlindSpots(this.mistakes, this.bank, Number(q.get("limit") ?? 3)));
    if ((m = route(/^\/api\/knowledge\/([^/]+)\/lesson$/))) {
      const code = decodeURIComponent(m[1]);
      if (!this.kp.node[code]) throw new HttpError(404, "找不到知识点");
      if (method === "POST") {
        const sample = this.fx.lessons?.[code];
        if (!sample) {
          const have = Object.keys(this.fx.lessons ?? {}).map((c) => this.kp.node[c]?.name).filter(Boolean).join("、");
          throw new HttpError(400, `预览版只准备了这几个知识点的示例讲解：${have}。装好以后，AI 会按孩子自己的错题现写。`);
        }
        const running = this.lessonState(code).job;
        if (running) return { job_id: running.id };
        const id = this.submit("kp_lesson", 3500, ["整理这个知识点的错题", "AI 正在写讲解"], { kp_code: code }, () => {
          this.lessons[code] = { ...clone(sample.lesson), created_at: now() };
        });
        this.lessonJobs[code] = id;
        return { job_id: id };
      }
      return this.lessonState(code);
    }
    if ((m = route(/^\/api\/knowledge\/([^/]+)$/))) {
      const code = decodeURIComponent(m[1]);
      if (!this.kp.node[code]) throw new HttpError(404, "找不到知识点");
      const { list, body } = this.kp.detail(code, this.mistakes, this.bank);
      return { ...body, mistake_list: list.map((x) => this.summary(x)) };
    }

    // 错题
    if (p === "/api/mistakes") {
      const subject = q.get("subject");
      const statuses = q.get("status")?.split(",").filter(Boolean);
      const kp = q.get("kp");
      return this.mistakes
        .filter((x) => (!subject || x.subject === subject) && (!statuses?.length || statuses.includes(x.status)))
        .filter((x) => !kp || x.kp_codes.some((c) => c === kp || c.startsWith(kp + ".")))
        .sort((x, y) => y.last_wrong_at.localeCompare(x.last_wrong_at))
        .map((x) => this.summary(x));
    }
    if ((m = route(/^\/api\/mistakes\/([^/]+)(\/attempts|\/solve|\/explain|\/tutor-done)?$/))) {
      const mk = this.mistake(m[1]);
      if (m[2] === "/explain") {
        return { job_id: this.submit("tutor_explain", 2500, ["整理题目和作答", "AI 正在讲解"], {}, () => {
          const steps = ["看清题目给了什么条件、问什么", "想一想这个条件对应哪条规律", "按规律一步一步算"];
          mk.explain = {
            read: "预览版里的讲解是写好的示例：先看题目考什么、关键条件是什么。", idea: "从关键条件想到对应的规律，再决定先算什么、后算什么。",
            steps, where_wrong: "孩子的作答错在把条件看反了；正式版会结合他的作答具体讲。", pitfalls: ["动笔前先把条件列出来"], answer: "见正式版",
            md: "**读题**　预览版里的讲解是写好的示例：先看题目考什么、关键条件是什么。\n\n**思路**　从关键条件想到对应的规律，再决定先算什么、后算什么。\n\n**分步**\n" +
              steps.map((x, i) => `${i + 1}. ${x}`).join("\n") + "\n\n**错在哪**　孩子的作答错在把条件看反了；正式版会结合他的作答具体讲。\n\n**下次提醒自己**\n- 动笔前先把条件列出来",
            created_at: new Date().toISOString(), model: "demo",
          };
          this.touch();
        }) };
      }
      if (m[2] === "/tutor-done") {
        if (mk.status === "TO_TUTOR") {
          mk.status = mk.gates.original ? "TO_VARIANT" : "TO_REDO";
          mk.status_name = mk.gates.original ? "待变式" : "待重做";
        }
        this.touch();
        return mk;
      }
      if (m[2] === "/attempts") {
        this.recordResult(mk, b.result, b.context ?? "redo");
        this.touch();
        return mk;
      }
      if (m[2] === "/solve") {
        if (["teacher", "manual", "answer_key"].includes(mk.question.answer_source)) throw new HttpError(400, "这道题已有老师或家长给的答案");
        return { job_id: this.submit("solve", 2500, ["AI 解答中"], {}, () => {
          mk.question.answer_source = mk.answer_source = "ai_unverified";
        }) };
      }
      if (method === "DELETE") {
        this.mistakes = this.mistakes.filter((x) => x.id !== mk.id);
        this.touch();
        return { ok: true };
      }
      if (method === "PATCH") {
        if (typeof b.answer === "string") {
          mk.question.answer = { final: b.answer };
          mk.answer_source = mk.question.answer_source = "manual";
        }
        if (b.kp_codes) {
          mk.kp_codes = b.kp_codes;
          mk.kp_names = this.kpNames(mk.subject, b.kp_codes);
        }
        if (b.error_causes) mk.error_causes = b.error_causes;
        this.touch();
      }
      return mk;
    }

    // 打印
    if (p === "/api/print-jobs" && method === "POST") {
      const template: string = b.template;
      const withKey = !!b.layout?.with_key;
      let picked: MistakeDetail[] = [];
      let title: string;
      let items: NonNullable<PrintJobInfo["items"]>;
      if (template === "page_restore") {
        const doc = this.docs[b.document_id];
        if (!doc) throw new HttpError(400, "请选择一份卷子");
        title = `原卷还原 · ${doc.title || SUBJECT_NAMES[doc.subject]}`;
        items = (doc.pages ?? []).map((pg, i) => ({ seq: i + 1, page_no: i + 1, mistake_id: null, instance_id: null,
          page_id: pg.id, number_label: null, status: null, status_name: null }));
      } else {
        const rank = (x: MistakeDetail) => this.fx.redo_order.indexOf(x.instance_id ?? "");
        picked = ((b.mistake_ids ?? []) as string[]).map((id) => this.mistake(id)).sort((x, y) => rank(x) - rank(y));
        if (!picked.length) throw new HttpError(400, "请至少选一道错题");
        title = `错题重做单 · ${picked.length} 题`;
        items = picked.map((x, i) => ({ seq: i + 1, page_no: 1, mistake_id: x.id, instance_id: x.instance_id,
          page_id: null, number_label: x.number_label, source: x.document?.title ?? SUBJECT_NAMES[x.subject],
          status: null, status_name: null }));
      }
      const { pages, count } = this.renderPages(template, b.document_id ?? null, picked, withKey);
      const job: PrintJobInfo = {
        id: uid(), template, template_name: template === "page_restore" ? "原卷还原" : "错题重做单", title, status: "rendering",
        page_count: null, error: null, layout: { paper: "A4", split_landscape: true, extra_space_mm: b.layout?.extra_space_mm ?? 0, with_key: withKey },
        created_at: now(), has_pdf: false, items,
      };
      this.prints.push(job);
      this.printPages[job.id] = pages;
      this.touch();
      const task = this.submit("print", 3000, ["排版", "生成 PDF"], { print_job_id: job.id }, () => {
        Object.assign(job, { status: "ready", page_count: count, has_pdf: true });
      });
      return { print_job_id: job.id, job_id: task };
    }
    if (p === "/api/print-jobs") {
      return [...this.prints].sort((x, y) => y.created_at.localeCompare(x.created_at)).map((x) => this.printJson(x, false));
    }
    if ((m = route(/^\/api\/print-jobs\/([^/]+)(\/results)?$/))) {
      const job = this.prints.find((x) => x.id === m![1]);
      if (!job) throw new HttpError(404, "找不到这次打印");
      if (!m[2]) return this.printJson(job, true);
      let recorded = 0;
      for (const r of (b.results ?? []) as { seq: number; result: string }[]) {
        const it = job.items?.find((x) => x.seq === r.seq);
        const mk = it?.mistake_id ? this.mistakes.find((x) => x.id === it.mistake_id) : undefined;
        if (!mk) continue;
        this.recordResult(mk, r.result, "redo");
        recorded += 1;
      }
      this.touch();
      return { recorded, ...this.printJson(job, true) };
    }

    throw new HttpError(404, `预览版没有模拟这个接口：${method} ${p}`);
  }
}

// 把 window.fetch 换成模拟后端：/api/* 在浏览器里处理，其他请求照常
export function installMockApi(fx: Fixtures): MockServer {
  const server = new MockServer(fx);
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(raw, "http://demo.local");
    if (!url.pathname.startsWith("/api/")) return realFetch(input, init);
    const method = (init?.method ?? "GET").toUpperCase();
    let body: Body | FormData | null = null;
    if (init?.body instanceof FormData) body = init.body;
    else if (typeof init?.body === "string") body = JSON.parse(init.body);
    await new Promise((r) => setTimeout(r, 120 + Math.random() * 150)); // 像真的网络请求一样稍等一下
    try {
      const data = server.handle(method, url, body);
      return new Response(JSON.stringify(clone(data)), { status: 200, headers: { "Content-Type": "application/json" } });
    } catch (err) {
      const status = err instanceof HttpError ? err.status : 500;
      return new Response(JSON.stringify({ detail: (err as Error).message }), { status, headers: { "Content-Type": "application/json" } });
    }
  };
  return server;
}

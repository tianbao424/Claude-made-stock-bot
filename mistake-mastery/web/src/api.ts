// 后端接口（见 docs/04 §5）。所有请求都带 Cookie；401 时跳到登录页。

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, credentials: "same-origin", headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(path, init);
  if (res.status === 401 && !path.startsWith("/api/login") && !path.startsWith("/api/session")) {
    const next = encodeURIComponent(location.pathname + location.search);
    location.href = `/login?next=${next}`;
    throw new ApiError(401, "请先登录");
  }
  if (!res.ok) {
    let msg = `请求失败（${res.status}）`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") msg = data.detail;
    } catch {
      /* 不是 JSON */
    }
    throw new ApiError(res.status, msg);
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T,>(p: string) => request<T>("GET", p),
  post: <T,>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}),
  patch: <T,>(p: string, b: unknown) => request<T>("PATCH", p, b),
  del: <T,>(p: string) => request<T>("DELETE", p),
  upload: <T,>(p: string, form: FormData) => request<T>("POST", p, form),
};

export type Subject = "math" | "physics";
export const SUBJECTS: { code: Subject; name: string }[] = [
  { code: "math", name: "数学" },
  { code: "physics", name: "物理" },
];
export const subjectName = (s: string) => SUBJECTS.find((x) => x.code === s)?.name ?? s;

export interface Student {
  id: string;
  name: string;
  grade: number;
  district: string | null;
  textbooks: Record<string, string>;
  settings: Record<string, unknown>;
}

export interface Job {
  id: string;
  kind: string;
  status: "queued" | "running" | "done" | "failed";
  progress: { stage: string; pct: number } | null;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface Doc {
  id: string;
  subject: Subject;
  source_kind: string;
  title: string | null;
  exam_date: string | null;
  mode: string;
  status: string;
  error: string | null;
  created_at: string;
  pages?: { id: string; page_no: number; erase_status: string; quality: { is_blurry?: boolean } | null; width: number; height: number; cw: number; ch: number }[];
}

export interface Option {
  key: string;
  md: string;
}
export interface SubQ {
  no: string;
  md: string;
}

export interface Candidate {
  instance_id: string;
  page_no: number;
  number_label: string;
  status: string;
  preselected: boolean;
  bbox: number[];
  question: {
    id: string;
    type: string;
    stem_md: string;
    options: Option[] | null;
    sub_questions: SubQ[] | null;
    answer: { final?: string } | null;
    answer_source: string;
    bj_slot: string | null;
    difficulty: number | null;
  };
  kp_codes: string[];
  grading: string | null;
  score: string | null;
  cause_suggestions: string[];
  student_answer: string | null;
}

export interface MistakeSummary {
  id: string;
  status: string;
  status_name: string;
  round: number;
  wrong_count: number;
  gates: { original?: boolean; variant?: boolean; spaced?: boolean };
  error_causes: string[];
  subject: Subject;
  question_type: string;
  stem_md: string;
  answer_source: string;
  bj_slot: string | null;
  difficulty: number | null;
  kp_codes: string[];
  kp_names: string[];
  instance_id: string | null;
  number_label: string | null;
  document: { id: string; title: string | null; source_kind: string; exam_date: string | null } | null;
  last_wrong_at: string;
  created_at: string;
  next_review_at: string | null;
}

export interface MistakeDetail extends MistakeSummary {
  question: {
    id: string;
    stem_md: string;
    options: Option[] | null;
    sub_questions: SubQ[] | null;
    answer: { final?: string } | null;
    solution_md: string | null;
    answer_source: string;
    verification: Record<string, unknown> | null;
  };
  instances: { id: string; page_id: string; number_label: string; student_answer: string | null; grading: string | null; score: string | null }[];
  attempts: { id: string; round: number; context: string; result: string; graded_by: string; error_cause: string | null; note: string | null; created_at: string }[];
}

export interface PrintJobInfo {
  id: string;
  template: string;
  template_name: string;
  title: string | null;
  status: string;
  page_count: number | null;
  error: string | null;
  layout: Record<string, unknown>;
  created_at: string;
  has_pdf: boolean;
  items?: { seq: number; page_no: number | null; mistake_id: string | null; instance_id: string | null; page_id: string | null; number_label: string | null; status: string | null; status_name: string | null }[];
}

export interface KpNode {
  code: string;
  name: string;
  level: number;
  children: KpNode[];
}

export interface Curriculum {
  tree: KpNode[];
  names: Record<string, string>;
  error_causes: { code: string; name: string; hint: string }[];
  bj_slots: { code: string; name: string }[];
  question_types: { code: string; name: string }[];
  source_kinds: { code: string; name: string }[];
  statuses: Record<string, string>;
}

export interface SyncStatus {
  enabled: boolean;
  is_git_repo: boolean;
  has_remote: boolean;
  dirty: boolean;
  unpushed_commits: number;
  last_synced_at: string | null;
  last_pushed_at: string | null;
  last_error: string | null;
}

const curriculumCache: Partial<Record<Subject, Promise<Curriculum>>> = {};
export function getCurriculum(subject: Subject): Promise<Curriculum> {
  curriculumCache[subject] ??= api.get<Curriculum>(`/api/curriculum/${subject}`);
  return curriculumCache[subject]!;
}

export const ANSWER_SOURCE: Record<string, string> = {
  teacher: "老师给的答案",
  answer_key: "答案页",
  manual: "家长填写",
  ai_unverified: "AI 解答 · 待核",
  ai_verified: "AI 解答 · 已交叉校验",
  none: "暂无答案",
};

export const GRADING: Record<string, string> = { wrong: "✗ 判错", partial: "½ 半对", right: "✓ 判对", none: "无批改" };

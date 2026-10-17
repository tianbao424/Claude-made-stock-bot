"""单题讲解：做错 → 待讲解 → AI 讲解这道题（看截图、针对作答）→ 讲完了 → 待重做；详情页带知识点讲解的链接。"""

from tests.conftest import synthetic_page


def _mistake(c):
    st = c.post("/api/students", json={"name": "小测"}).json()
    r = c.post("/api/captures", data={"student_id": st["id"], "subject": "math", "mode": "page", "source_kind": "monthly"},
               files=[("files", ("p1.jpg", synthetic_page(), "image/jpeg"))])
    doc = r.json()["document_id"]
    cand = c.get(f"/api/documents/{doc}/candidates").json()["items"]
    c.post(f"/api/documents/{doc}/confirm", json={"items": [{"instance_id": cand[0]["instance_id"], "selected": True}]})
    return st["id"], c.get(f"/api/mistakes?student_id={st['id']}").json()[0]["id"]


def test_explain_mistake_and_tutor_done(logged_in):
    c = logged_in
    sid, mid = _mistake(c)
    d = c.get(f"/api/mistakes/{mid}").json()
    assert d["explain"] is None and d["explain_job"] is None and d["kp_lessons"] == []

    # 重做又错：待讲解
    d = c.post(f"/api/mistakes/{mid}/attempts", json={"result": "wrong", "context": "redo"}).json()
    assert d["status"] == "TO_TUTOR"

    seen = []
    base = c.app_ctx.llm.fake

    def fake(task, messages):
        if task == "tutor":
            seen.append(messages)
        if task == "lesson":
            return {"one_line": "二次函数图象", "key_points": [{"title": "开口", "md": "$a>0$ 开口向上"}], "method": ["先看 $a$"],
                    "pitfalls": [], "example": None, "self_check": []}
        return base(task, messages)

    c.app_ctx.llm.fake = fake
    r = c.post(f"/api/mistakes/{mid}/explain", json={})
    assert r.status_code == 200 and c.get(f"/api/jobs/{r.json()['job_id']}").json()["status"] == "done"
    content = seen[0][-1]["content"]
    assert content[0]["type"] == "image_url"  # 带着题目截图
    text = content[1]["text"]
    assert "孩子的作答" in text and "小测" not in text  # 不带孩子的名字
    d = c.get(f"/api/mistakes/{mid}").json()
    ex = d["explain"]
    assert ex["steps"] == ["配方：$y=(x-1)^2-1$", "对称轴 $x=1$，顶点 $(1,-1)$"] and "**错在哪**" in ex["md"] and ex["answer"] == "B"

    # 讲完了 → 待重做
    d = c.post(f"/api/mistakes/{mid}/tutor-done").json()
    assert d["status"] == "TO_REDO"

    # 这个知识点有讲解后，详情里能看到链接
    c.post("/api/knowledge/M.FUN.QUAD.GRAPH/lesson", json={"student_id": sid})
    d = c.get(f"/api/mistakes/{mid}").json()
    assert d["kp_lessons"] == ["M.FUN.QUAD.GRAPH"]

import json
import os
import tempfile

os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")

from fastapi.testclient import TestClient  # noqa: E402

from app.agents.flashcards import sm2  # noqa: E402
from app.main import app  # noqa: E402

H = {"X-Learner-Id": "test-learner"}


def test_quiz_flow_and_stats():
    with TestClient(app) as c:
        q = c.get("/quiz/next", headers=H).json()
        assert "stem" in q and len(q["options"]) >= 2 and "answer" not in q
        r = c.post("/quiz/submit", json={"question_id": q["id"], "choice": 0}, headers=H).json()
        assert "correct" in r and r["explanation"]
        assert len(c.get("/quiz/stats", headers=H).json()) == 1


def test_requires_learner_header():
    with TestClient(app) as c:
        assert c.get("/quiz/next").status_code == 400


def test_planner():
    with TestClient(app) as c:
        assert c.get("/planner/plan", headers=H).status_code == 404
        c.put("/planner/profile", json={"exam_date": "2099-01-01", "hours_per_day": 5}, headers=H)
        p = c.get("/planner/plan", headers=H).json()
        assert len(p["plan"]) == 19 and p["revision_days"] == 14


def test_cards_and_sm2():
    with TestClient(app) as c:
        cid = c.post("/cards", json={"front": "PFK-1?", "back": "Rate-limiting glycolysis"}, headers=H).json()["id"]
        assert len(c.get("/cards/due", headers=H).json()) == 1
        assert c.post(f"/cards/{cid}/review", json={"quality": 5}, headers=H).json()["interval"] == 1
        assert c.get("/cards/due", headers=H).json() == []
    assert sm2(2.5, 6, 2, 1)[1:] == (1, 0)


def test_tutor_retrieval(tmp_path, monkeypatch):
    import app.retrieval as r
    import app.ingest as ing
    monkeypatch.setattr(r, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(ing, "CONTENT_DIR", tmp_path)
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "n.md").write_text("Magnesium sulphate antidote is calcium gluconate in eclampsia toxicity.")
    ing.main([])
    r.reload()
    with TestClient(app) as c:
        out = c.post("/tutor/ask", json={"question": "antidote for magnesium toxicity"}, headers=H).json()
        assert out["sources"] and "calcium gluconate" in out["sources"][0]["snippet"]
    r.reload()


def test_generate_questions_from_library(tmp_path, monkeypatch):
    import json

    import app.agents.generate as gen
    import app.ingest as ing
    import app.retrieval as r
    monkeypatch.setattr(r, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(ing, "CONTENT_DIR", tmp_path)
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "a.md").write_text(
        "source: Test Book (CC BY)\ntitle: Heart\n\nThe sinoatrial node is the pacemaker of the heart.")
    ing.main([])
    r.reload()
    fake = json.dumps([{"subject": "Physiology", "topic": "Heart", "stem": "Pacemaker of the heart?",
                        "options": ["SA node", "AV node", "Purkinje", "Bundle of His"], "answer": 0,
                        "explanation": "SA node sets the rate."}])
    monkeypatch.setattr(gen.llm, "available", lambda *a: True)
    monkeypatch.setattr(gen.llm, "complete", lambda *a, **k: fake)
    with TestClient(app) as c:
        made = gen.questions("sinoatrial pacemaker", 1)["made"]
        assert made and made[0]["source"] == "Test Book (CC BY) / Heart"
        assert gen.questions("sinoatrial pacemaker", 1, source="Other Book")["made"] == []
        stats = c.get("/library/stats", headers=H).json()
        assert stats["chunks"] >= 1
    r.reload()


def test_header_parsing():
    from app.ingest import split_header
    meta, body = split_header("source: X\ntitle: Y\n\nhello", "f.md")
    assert meta == {"source": "X", "title": "Y"} and body.strip() == "hello"


def test_medmcqa_import(tmp_path, monkeypatch):
    import json

    import app.import_medmcqa as imp
    f = tmp_path / "train.json"
    rows = [
        {"id": "a1", "question": "Drug of choice for eclampsia?", "opa": "Diazepam", "opb": "MgSO4", "opc": "Phenytoin",
         "opd": "Labetalol", "cop": 1, "exp": "MgSO4 is used.", "subject_name": "Gynaecology & Obstetrics", "topic_name": "Eclampsia"},
        {"id": "a2", "question": "Dental q", "opa": "a", "opb": "b", "opc": "c", "opd": "d", "cop": 0, "exp": "x", "subject_name": "Dental", "topic_name": "t"},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(imp, "CONTENT_DIR", tmp_path)
    imp.main(str(f), 10)
    from app.db import conn
    with conn() as c:
        row = c.execute("SELECT subject, answer FROM questions WHERE id='mm-a1'").fetchone()
        assert row["subject"] == "Obstetrics and Gynaecology" and row["answer"] == 1
        assert c.execute("SELECT COUNT(*) n FROM questions WHERE id='mm-a2'").fetchone()["n"] == 0
    assert (tmp_path / "raw" / "medmcqa" / "Obstetrics_and_Gynaecology.md").exists()


def test_mock_exam_flow():
    import time

    from app.db import conn
    with TestClient(app) as c:
        m = c.post("/mock/start", json={"preset": "quick"}, headers=H).json()
        assert m["total"] >= 1 and m["seconds_left"] > 1100 and "answer" not in m["questions"][0]
        assert c.get(f"/mock/{m['id']}/result", headers=H).json()["status"] == "in_progress"
        q0 = m["questions"][0]
        assert c.put(f"/mock/{m['id']}/answer", json={"question_id": q0["id"], "choice": 1}, headers=H).status_code == 200
        r = c.post(f"/mock/{m['id']}/submit", headers=H).json()
        assert r["status"] == "submitted" and r["total"] == m["total"] and r["answered"] == 1
        assert r["review"][0]["explanation"] and 0 <= r["score"] <= 1
        # answers are rejected after submit, and other learners cannot see the exam
        assert c.put(f"/mock/{m['id']}/answer", json={"question_id": q0["id"], "choice": 0}, headers=H).status_code == 409
        assert c.get(f"/mock/{m['id']}", headers={"X-Learner-Id": "someone-else"}).status_code == 404
        # time expiry auto-submits
        m2 = c.post("/mock/start", json={"preset": "quick"}, headers=H).json()
        with conn() as db:
            db.execute("UPDATE mocks SET started=? WHERE id=?", (int(time.time()) - 99999, m2["id"]))
        assert c.get(f"/mock/{m2['id']}", headers=H).json()["status"] == "submitted"
        assert c.put(f"/mock/{m2['id']}/answer", json={"question_id": q0["id"], "choice": 0}, headers=H).status_code == 409
        assert c.post("/mock/start", json={"preset": "nope"}, headers=H).status_code == 400


def test_passcode_gate(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "ACCESS_CODE", "letmein")
    with TestClient(app) as c:
        assert c.get("/health").json()["locked"] is True
        assert c.get("/quiz/next", headers=H).status_code == 401
        assert c.get("/quiz/next", headers={**H, "X-Access-Code": "wrong"}).status_code == 401
        assert c.get("/quiz/next", headers={**H, "X-Access-Code": "letmein"}).status_code == 200


def _pdf(text=None, image_text=None):
    import io

    import pymupdf
    from PIL import Image, ImageDraw
    d = pymupdf.open()
    pg = d.new_page()
    if text:
        pg.insert_text((72, 100), text)
    if image_text:  # a scanned page: only pixels, no text layer
        im = Image.new("RGB", (1600, 300), "white")
        ImageDraw.Draw(im).text((40, 100), image_text, fill="black", font_size=70)
        b = io.BytesIO()
        im.save(b, "PNG")
        pg.insert_image(pg.rect, stream=b.getvalue())
    return d.tobytes()


def test_upload_pdf_with_text_and_scanned_pages():
    import app.library as lib
    lib.RUN_SYNC = True
    with TestClient(app) as c:
        me = {"X-Learner-Id": "uploader"}
        r = c.post("/library/upload", files={"file": ("notes.pdf", _pdf(text="The sinoatrial node paces the heart and sets sinus rhythm."), "application/pdf")}, headers=me)
        assert r.status_code == 200
        docs = c.get("/library/docs", headers=me).json()
        assert docs[0]["status"] == "ready" and docs[0]["pages_done"] == 1
        hits = lib.search_user("uploader", "sinoatrial node")
        assert hits and "sinoatrial" in hits[0]["text"]
        c.post("/library/upload", files={"file": ("scan.pdf", _pdf(image_text="Nephron filtration glomerulus"), "application/pdf")}, headers=me)
        assert any("glomerulus" in h["text"].lower() for h in lib.search_user("uploader", "glomerulus"))
        other = {"X-Learner-Id": "someone-else"}
        assert lib.search_user("someone-else", "sinoatrial") == []
        assert c.get("/library/docs", headers=other).json() == []
        assert c.delete(f"/library/docs/{docs[-1]['id']}", headers=other).status_code == 404
        assert c.delete(f"/library/docs/{docs[-1]['id']}", headers=me).status_code == 200


def test_upload_text_and_unsupported_type():
    import app.library as lib
    lib.RUN_SYNC = True
    with TestClient(app) as c:
        me = {"X-Learner-Id": "u2"}
        c.post("/library/upload", files={"file": ("a.txt", b"Warfarin inhibits vitamin K epoxide reductase.", "text/plain")}, headers=me)
        c.post("/library/upload", files={"file": ("a.exe", b"x", "application/octet-stream")}, headers=me)
        st = {d["name"]: d["status"] for d in c.get("/library/docs", headers=me).json()}
        assert st == {"a.txt": "ready", "a.exe": "error"}


def test_link_import_blocks_internal_addresses_and_reads_pages(monkeypatch):
    import app.library as lib
    lib.RUN_SYNC = True
    with TestClient(app) as c:
        me = {"X-Learner-Id": "u3"}
        for bad in ("http://127.0.0.1:8000/health", "http://169.254.169.254/latest/meta-data", "file:///etc/passwd"):
            c.post("/library/link", json={"url": bad}, headers=me)
        docs = c.get("/library/docs", headers=me).json()
        assert len(docs) == 3 and all(d["status"] == "error" for d in docs)
        monkeypatch.setattr(lib, "fetch", lambda url, *a: (b"<html><body><script>x()</script><p>Insulin lowers blood glucose.</p></body></html>", "text/html", url))
        c.post("/library/link", json={"url": "https://example.org/page"}, headers=me)
        assert lib.search_user("u3", "insulin glucose")
    assert lib.normalize_link("https://drive.google.com/file/d/ABC_123/view?usp=sharing") == "https://drive.google.com/uc?export=download&id=ABC_123"


def test_questions_from_own_upload_stay_private_and_feed_mock(monkeypatch):
    import app.agents.generate as gen
    import app.library as lib
    lib.RUN_SYNC = True
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    qjson = json.dumps([{"subject": "Physiology", "topic": "Heart", "stem": "Which structure paces the heart?",
                         "options": ["SA node", "AV node", "Purkinje", "Bundle of His"], "answer": 0,
                         "explanation": "The SA node has the fastest intrinsic rate."}])
    monkeypatch.setattr(gen.llm, "complete", lambda *a, **k: qjson)
    with TestClient(app) as c:
        mine, theirs = {"X-Learner-Id": "u4"}, {"X-Learner-Id": "u5"}
        c.post("/library/upload", files={"file": ("h.txt", b"The sinoatrial node paces the heart and sets the rhythm.", "text/plain")}, headers=mine)
        out = c.post("/quiz/generate", json={"topic": "sinoatrial", "n": 1, "source": "h.txt"}, headers=mine).json()
        assert len(out["made"]) == 1 and out["made"][0]["id"].startswith("own-")
        m = c.post("/mock/start", json={"preset": "my_material"}, headers=mine).json()
        assert m["total"] == 1
        assert c.post("/mock/start", json={"preset": "my_material"}, headers=theirs).status_code == 404
        seen = {c.get("/quiz/next", headers=theirs).json()["id"] for _ in range(30)}
        assert out["made"][0]["id"] not in seen


def test_options_shuffle_but_grading_stays_correct():
    from app.db import conn
    with TestClient(app) as c:
        me = {"X-Learner-Id": "shuffler"}
        orders = set()
        for _ in range(40):
            q = c.get("/quiz/next?subject=Anatomy", headers=me).json()
            with conn() as db:
                row = db.execute("SELECT options, answer FROM questions WHERE id=?", (q["id"],)).fetchone()
            orig = json.loads(row["options"])
            assert sorted(q["options"]) == sorted(orig)
            orders.add(tuple(q["options"]))
            right = q["options"].index(orig[row["answer"]])
            r = c.post("/quiz/submit", json={"question_id": q["id"], "choice": right}, headers=me).json()
            assert r["correct"] is True and r["answer"] == right
        assert len(orders) > 5  # the same question appears in different orders

        m = c.post("/mock/start", json={"preset": "quick"}, headers=me).json()
        for qq in m["questions"]:
            with conn() as db:
                row = db.execute("SELECT options, answer FROM questions WHERE id=?", (qq["id"],)).fetchone()
            orig = json.loads(row["options"])
            right = qq["options"].index(orig[row["answer"]])
            c.put(f"/mock/{m['id']}/answer", json={"question_id": qq["id"], "choice": right}, headers=me)
        again = c.get(f"/mock/{m['id']}", headers=me).json()  # reopening keeps the same order and saved answers
        assert [x["options"] for x in again["questions"]] == [x["options"] for x in m["questions"]]
        res = c.post(f"/mock/{m['id']}/submit", headers=me).json()
        assert res["score"] == res["total"] == m["total"]
        assert all(r["chosen"] == r["answer"] for r in res["review"])


def test_build_bank_saves_questions_for_next_deploy(tmp_path, monkeypatch):
    import app.agents.generate as gen
    import app.build_bank as bb
    from app.db import conn
    monkeypatch.setattr(bb, "OUT", tmp_path / "generated.json")
    def fake(topic=None, n=5, source=None, learner=None):
        with conn() as c:
            c.execute("INSERT OR IGNORE INTO questions (id, subject, topic, stem, options, answer, explanation, source, reviewed, owner) "
                      "VALUES ('gen-zz1','Physiology','Heart','Fake stem?',?,1,'why','Test Book',0,NULL)",
                      (json.dumps(["a", "b", "c", "d"]),))
        return {"made": [{"id": "gen-zz1"}]}
    monkeypatch.setattr(gen, "questions", fake)
    assert bb.main(1, 1) == 1
    saved = json.loads((tmp_path / "generated.json").read_text())
    ids = [q["id"] for q in saved]
    assert "gen-zz1" in ids and next(q for q in saved if q["id"] == "gen-zz1")["options"] == ["a", "b", "c", "d"]
    assert bb.main(1, 1) == 1  # running again does not duplicate
    assert len(json.loads((tmp_path / "generated.json").read_text())) == len(ids)


def test_private_chunks_hidden_without_code(monkeypatch):
    from app import retrieval
    chunks = [{"source": "Pub", "title": "", "text": "aspirin inhibits cox"}, {"source": "Priv", "title": "", "text": "aspirin secret private note", "private": True}]
    from rank_bm25 import BM25Okapi
    monkeypatch.setattr(retrieval, "_index", lambda: (chunks, BM25Okapi([retrieval._tok(c["text"]) for c in chunks])))
    assert {h["source"] for h in retrieval.search("aspirin")} == {"Pub"}
    tok = retrieval.unlocked.set(True)
    try:
        assert {h["source"] for h in retrieval.search("aspirin")} == {"Pub", "Priv"}
    finally:
        retrieval.unlocked.reset(tok)

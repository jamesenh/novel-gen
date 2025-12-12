import json
import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from novelgen.api.main import app
import novelgen.services.project_service as project_service
import novelgen.services.export_service as export_service
import novelgen.services.generation_service as generation_service


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@pytest.fixture
def sample_project(tmp_path, monkeypatch):
    # 将项目根指向临时目录
    monkeypatch.setattr(project_service, "PROJECTS_ROOT", str(tmp_path))
    monkeypatch.setattr(export_service, "PROJECTS_ROOT", str(tmp_path))

    project_dir = tmp_path / "demo"
    chapters_dir = project_dir / "chapters"
    chapters_dir.mkdir(parents=True)

    # settings (不再包含 world_description/theme_description，由独立 JSON 文件管理)
    _write_json(
        project_dir / "settings.json",
        {
            "project_name": "demo",
            "author": "Jamesenh",
            "initial_chapters": 1,
            "max_chapters": 10,
        },
    )
    # world / characters / outline
    _write_json(
        project_dir / "world.json",
        {
            "world_name": "灵虚大陆",
            "time_period": "远古",
            "geography": "群山",
            "social_system": "门派林立",
            "technology_level": "修真文明",
            "culture_customs": "修行者敬畏天地",
        },
    )
    _write_json(
        project_dir / "theme_conflict.json",
        {
            "themes": ["成长", "冲突"],
            "conflicts": ["门派与世俗"],
        },
    )
    _write_json(
        project_dir / "characters.json",
        {
            "protagonist": {
                "name": "林轩",
                "role": "主角",
                "gender": "男",
                "appearance": "黑发少年",
                "personality": "坚韧",
                "background": "小宗门弟子",
                "motivation": "守护宗门",
            },
            "antagonist": None,
            "supporting_characters": [],
        },
    )
    _write_json(
        project_dir / "outline.json",
        {
            "story_premise": "凡人成仙",
            "beginning": "拜入宗门",
            "development": "秘境试炼",
            "climax": "大战",
            "resolution": "得道飞升",
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_title": "山门初识",
                    "summary": "主角进入宗门",
                    "key_events": ["拜师"],
                    "dependencies": [],
                    "timeline_anchor": None,
                }
            ],
            "is_complete": True,
            "current_phase": "complete",
        },
    )

    # chapter file
    _write_json(
        chapters_dir / "chapter_001.json",
        {
            "chapter_number": 1,
            "chapter_title": "山门初识",
            "scenes": [
                {"scene_number": 1, "content": "抵达山门。", "word_count": 6},
                {"scene_number": 2, "content": "拜见师尊。", "word_count": 5},
            ],
            "total_words": 11,
        },
    )
    _write_json(
        chapters_dir / "chapter_002.json",
        {
            "chapter_number": 2,
            "chapter_title": "秘境初探",
            "scenes": [{"scene_number": 1, "content": "进入秘境。", "word_count": 5}],
            "total_words": 5,
        },
    )
    _write_json(chapters_dir / "chapter_001_plan.json", {"scenes": []})
    # scene file用于回滚测试
    _write_json(chapters_dir / "scene_001_002.json", {"content": "额外场景2"})
    _write_json(chapters_dir / "scene_001_003.json", {"content": "额外场景"})
    _write_json(chapters_dir / "scene_002_001.json", {"content": "第二章场景"})

    return project_dir


@pytest.fixture
def client(sample_project):
    return TestClient(app)


def test_project_list_and_detail(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data and data[0]["name"] == "demo"

    detail = client.get("/api/projects/demo")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["summary"]["name"] == "demo"

    state = client.get("/api/projects/demo/state")
    assert state.status_code == 200
    steps = state.json()["steps"]
    assert steps["world"] and steps["outline"] and steps["chapters"]


def test_project_creation(client):
    payload = {
        "project_name": "new_proj",
        "initial_chapters": 2,
    }
    resp = client.post("/api/projects", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["summary"]["name"] == "new_proj"


def test_generation_lifecycle(client, monkeypatch):
    calls = {}

    def fake_start(project_name, stop_at, verbose, show_prompt):
        calls["start"] = (project_name, stop_at, verbose, show_prompt)
        return "task-1"

    def fake_resume(project_name):
        calls["resume"] = project_name
        return "task-2"

    def fake_stop(project_name):
        calls["stop"] = project_name
        return "task-1"

    def fake_status(project_name):
        return {"status": "running", "task_id": "task-1", "detail": None}

    def fake_progress(project_name):
        return {
            "status": "running",
            "progress_percent": 50.0,
            "current_step": "outline_creation",
            "current_chapter": 1,
            "current_scene": None,
            "message": "进行中",
        }

    def fake_logs(project_name, limit=50):
        return [
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "log1", "context": {}}
        ]

    monkeypatch.setattr(generation_service, "start_generation", fake_start)
    monkeypatch.setattr(generation_service, "resume_generation", fake_resume)
    monkeypatch.setattr(generation_service, "stop_generation", fake_stop)
    monkeypatch.setattr(generation_service, "get_status", fake_status)
    monkeypatch.setattr(generation_service, "read_progress", fake_progress)
    monkeypatch.setattr(generation_service, "read_logs", fake_logs)

    start_resp = client.post("/api/projects/demo/generate", json={"stop_at": "outline_creation", "verbose": True})
    assert start_resp.status_code == 202
    assert calls["start"] == ("demo", "outline_creation", True, False)

    resume_resp = client.post("/api/projects/demo/generate/resume")
    assert resume_resp.status_code == 202
    assert calls["resume"] == "demo"

    status_resp = client.get("/api/projects/demo/generate/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "running"

    progress_resp = client.get("/api/projects/demo/generate/progress")
    assert progress_resp.status_code == 200
    assert progress_resp.json()["current_step"] == "outline_creation"

    logs_resp = client.get("/api/projects/demo/generate/logs")
    assert logs_resp.status_code == 200
    assert len(logs_resp.json()["items"]) == 1

    stop_resp = client.post("/api/projects/demo/generate/stop")
    assert stop_resp.status_code == 200
    assert calls["stop"] == "demo"


def test_generation_conflict_returns_409(client, monkeypatch):
    def raise_conflict(*args, **kwargs):
        raise ValueError("running")

    monkeypatch.setattr(generation_service, "start_generation", raise_conflict)
    resp = client.post("/api/projects/demo/generate", json={})
    assert resp.status_code == 409


def test_content_apis(client):
    world = client.get("/api/projects/demo/world")
    assert world.status_code == 200
    assert world.json()["world_name"] == "灵虚大陆"

    chapters = client.get("/api/projects/demo/chapters")
    assert chapters.status_code == 200
    assert len(chapters.json()) == 2

    chapter = client.get("/api/projects/demo/chapters/1")
    assert chapter.status_code == 200
    body = chapter.json()
    assert body["chapter_title"] == "山门初识"
    assert len(body["scenes"]) == 2


def test_export_endpoints(client):
    full = client.get("/api/projects/demo/export/txt")
    assert full.status_code == 200
    assert "text/plain" in full.headers["content-type"]
    assert "山门初识" in full.text

    single = client.get("/api/projects/demo/export/txt/1")
    assert single.status_code == 200
    assert "第" in single.text

    md_full = client.get("/api/projects/demo/export/md")
    assert md_full.status_code == 200
    assert "text/markdown" in md_full.headers["content-type"]

    json_full = client.get("/api/projects/demo/export/json")
    assert json_full.status_code == 200
    parsed = json.loads(json_full.content.decode("utf-8"))
    assert parsed and parsed[0]["chapter_title"] == "山门初识"


def test_update_world_characters_outline(client):
    resp = client.put("/api/projects/demo/world", json={"world_name": "新世界", "culture_customs": "新风俗"})
    assert resp.status_code == 200
    world = client.get("/api/projects/demo/world").json()
    assert world["world_name"] == "新世界"
    assert world["culture_customs"] == "新风俗"

    resp = client.put(
        "/api/projects/demo/characters",
        json={
            "protagonist": {"name": "李青", "role": "主角"},
            "supporting_characters": [{"name": "配角A", "role": "朋友"}],
        },
    )
    assert resp.status_code == 200
    chars = client.get("/api/projects/demo/characters").json()
    assert chars["protagonist"]["name"] == "李青"
    assert len(chars["supporting_characters"]) == 1

    resp = client.put(
        "/api/projects/demo/outline",
        json={"story_premise": "新前提", "development": "新发展"},
    )
    assert resp.status_code == 200
    outline = client.get("/api/projects/demo/outline").json()
    assert outline["story_premise"] == "新前提"
    assert outline["development"] == "新发展"


def test_rollback_by_step_clears_following_outputs(client, monkeypatch):
    monkeypatch.setattr(generation_service, "reset_runtime_state", lambda *a, **k: 2)
    resp = client.post("/api/projects/demo/rollback", json={"step": "character_creation"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["deleted_files"] >= 4
    assert payload["cleared_memories"] == 2

    project_root = project_service.PROJECTS_ROOT
    assert os.path.exists(os.path.join(project_root, "demo", "world.json"))
    assert not os.path.exists(os.path.join(project_root, "demo", "characters.json"))
    assert not os.path.exists(os.path.join(project_root, "demo", "outline.json"))
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "chapter_001.json"))
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "chapter_001_plan.json"))


def test_rollback_chapter_keeps_plan(client, monkeypatch):
    monkeypatch.setattr(generation_service, "reset_runtime_state", lambda *a, **k: 1)
    resp = client.post("/api/projects/demo/rollback", json={"chapter": 1})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["deleted_files"] >= 3

    project_root = project_service.PROJECTS_ROOT
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "chapter_001.json"))
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "scene_001_003.json"))
    # 章节计划文件应保留
    assert os.path.exists(os.path.join(project_root, "demo", "chapters", "chapter_001_plan.json"))


def test_rollback_scene_removes_scene_and_chapter_file(client, monkeypatch):
    monkeypatch.setattr(generation_service, "reset_runtime_state", lambda *a, **k: 3)
    resp = client.post("/api/projects/demo/rollback", json={"chapter": 1, "scene": 2})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["cleared_memories"] == 3

    project_root = project_service.PROJECTS_ROOT
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "scene_001_002.json"))
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "scene_001_003.json"))
    # 合并章节应删除
    assert not os.path.exists(os.path.join(project_root, "demo", "chapters", "chapter_001.json"))


def test_update_chapter_and_delete_scene(client):
    payload = {
        "chapter_title": "改名章节",
        "scenes": [
            {"scene_number": 1, "content": "新的内容一"},
            {"scene_number": 2, "content": "新的内容二", "word_count": 5},
        ],
    }
    resp = client.put("/api/projects/demo/chapters/1", json=payload)
    assert resp.status_code == 200

    chapter = client.get("/api/projects/demo/chapters/1").json()
    assert chapter["chapter_title"] == "改名章节"
    assert len(chapter["scenes"]) == 2

    del_resp = client.delete("/api/projects/demo/chapters/1", params={"scene": 2})
    assert del_resp.status_code == 200
    chapter_after = client.get("/api/projects/demo/chapters/1").json()
    assert len(chapter_after["scenes"]) == 1
    assert chapter_after["scenes"][0]["scene_number"] == 1


def test_delete_chapter(client):
    resp = client.delete("/api/projects/demo/chapters/2")
    assert resp.status_code == 200
    chapters = client.get("/api/projects/demo/chapters").json()
    nums = [c["chapter_number"] for c in chapters]
    assert 2 not in nums


def test_delete_project_success(client, monkeypatch):
    """测试成功删除项目"""
    # 模拟 generation_service 的清理函数
    calls = {}

    def fake_stop(project_name):
        calls["stop"] = project_name
        return None

    def fake_clear(project_name):
        calls["clear"] = project_name
        return 3

    monkeypatch.setattr(generation_service, "stop_generation", fake_stop)
    monkeypatch.setattr(generation_service, "clear_runtime_state", fake_clear)

    # 确保项目存在
    project_root = project_service.PROJECTS_ROOT
    assert os.path.exists(os.path.join(project_root, "demo"))

    # 删除项目
    resp = client.delete("/api/projects/demo")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["deleted"] is True
    assert payload["project_name"] == "demo"
    assert payload["details"]["deleted_files"] is True
    assert payload["details"]["cleared_redis"] == 3

    # 确认项目目录已删除
    assert not os.path.exists(os.path.join(project_root, "demo"))

    # 确认清理函数被调用
    assert calls["stop"] == "demo"
    assert calls["clear"] == "demo"


def test_delete_project_not_found(client):
    """测试删除不存在的项目返回 404"""
    resp = client.delete("/api/projects/nonexistent_project")
    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]


def test_delete_project_with_mem0_cleanup(tmp_path, monkeypatch):
    """测试删除项目时 Mem0 清理分支"""
    # 设置临时项目根目录
    monkeypatch.setattr(project_service, "PROJECTS_ROOT", str(tmp_path))
    monkeypatch.setattr(export_service, "PROJECTS_ROOT", str(tmp_path))

    # 创建项目
    project_dir = tmp_path / "mem0_test"
    project_dir.mkdir()
    _write_json(
        project_dir / "settings.json",
        {
            "project_name": "mem0_test",
            "author": "Jamesenh",
            "initial_chapters": 1,
            "max_chapters": 10,
        },
    )

    # 模拟 generation_service
    monkeypatch.setattr(generation_service, "stop_generation", lambda *a: None)
    monkeypatch.setattr(generation_service, "clear_runtime_state", lambda *a: 0)

    # 模拟 Mem0Manager（不实际初始化）
    mem0_calls = {}

    class MockMem0Manager:
        def __init__(self, **kwargs):
            mem0_calls["init"] = kwargs

        def clear_project_memory(self):
            mem0_calls["clear"] = True
            return True

        def close(self, timeout=5.0):
            mem0_calls["close"] = True

    # 由于 Mem0 默认未启用，这里只测试不会报错的场景
    test_client = TestClient(app)
    resp = test_client.delete("/api/projects/mem0_test")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert not os.path.exists(project_dir)


def test_delete_project_cleans_vector_dir_inside_project(tmp_path, monkeypatch):
    """测试删除项目时清理项目内的向量存储目录"""
    monkeypatch.setattr(project_service, "PROJECTS_ROOT", str(tmp_path))
    monkeypatch.setattr(export_service, "PROJECTS_ROOT", str(tmp_path))

    # 创建项目和向量目录
    project_dir = tmp_path / "vector_test"
    project_dir.mkdir()
    vector_dir = project_dir / "data" / "vectors"
    vector_dir.mkdir(parents=True)
    (vector_dir / "test.bin").write_text("dummy")

    _write_json(
        project_dir / "settings.json",
        {
            "project_name": "vector_test",
            "author": "Jamesenh",
            "initial_chapters": 1,
            "max_chapters": 10,
        },
    )

    monkeypatch.setattr(generation_service, "stop_generation", lambda *a: None)
    monkeypatch.setattr(generation_service, "clear_runtime_state", lambda *a: 0)

    test_client = TestClient(app)
    resp = test_client.delete("/api/projects/vector_test")
    assert resp.status_code == 200

    # 确认整个项目目录（包括向量目录）已被删除
    assert not os.path.exists(project_dir)
    assert not os.path.exists(vector_dir)



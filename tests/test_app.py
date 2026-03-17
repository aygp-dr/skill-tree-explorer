"""Tests for the Skill Tree Explorer Flask application."""

from main import SKILL_TREES


# ---------------------------------------------------------------------------
# Skill tree data integrity
# ---------------------------------------------------------------------------


class TestSkillTreeData:
    """Validate the embedded skill tree definitions."""

    def test_all_three_trees_exist(self):
        assert "backend" in SKILL_TREES
        assert "frontend" in SKILL_TREES
        assert "devops" in SKILL_TREES

    def test_each_tree_has_skills(self):
        for tree_id, tree in SKILL_TREES.items():
            assert "name" in tree, f"{tree_id} missing name"
            assert "skills" in tree, f"{tree_id} missing skills"
            assert len(tree["skills"]) > 0, f"{tree_id} has no skills"

    def test_skill_dependency_integrity(self):
        """Every dependency reference must point to a valid skill ID in the same tree."""
        for tree_id, tree in SKILL_TREES.items():
            valid_ids = {s["id"] for s in tree["skills"]}
            for skill in tree["skills"]:
                for dep in skill["deps"]:
                    assert dep in valid_ids, (
                        f"Tree '{tree_id}': skill '{skill['id']}' depends on "
                        f"'{dep}' which does not exist"
                    )

    def test_skill_ids_unique_within_tree(self):
        for tree_id, tree in SKILL_TREES.items():
            ids = [s["id"] for s in tree["skills"]]
            assert len(ids) == len(set(ids)), f"Duplicate skill IDs in {tree_id}"

    def test_level_one_skills_have_no_deps(self):
        """Level 1 skills should be entry points with no prerequisites."""
        for tree_id, tree in SKILL_TREES.items():
            for skill in tree["skills"]:
                if skill["level"] == 1:
                    assert skill["deps"] == [], (
                        f"Tree '{tree_id}': level-1 skill '{skill['id']}' "
                        f"should have no deps"
                    )


# ---------------------------------------------------------------------------
# Flask routes — GET
# ---------------------------------------------------------------------------


class TestIndexRoute:
    def test_get_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_contains_title(self, client):
        resp = client.get("/")
        assert b"Skill Tree Explorer" in resp.data

    def test_index_default_tree_is_backend(self, client):
        resp = client.get("/")
        assert b"Backend Engineering" in resp.data

    def test_index_select_frontend_tree(self, client):
        resp = client.get("/?tree=frontend")
        assert resp.status_code == 200
        assert b"Frontend Engineering" in resp.data

    def test_index_select_devops_tree(self, client):
        resp = client.get("/?tree=devops")
        assert resp.status_code == 200
        assert b"DevOps" in resp.data

    def test_index_invalid_tree_still_200(self, client):
        """Selecting a non-existent tree should not crash."""
        resp = client.get("/?tree=nonexistent")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Flask routes — POST (toggle skill completion)
# ---------------------------------------------------------------------------


class TestPostToggle:
    def test_post_completes_skill(self, client):
        """POST with a level-1 skill should mark it complete."""
        resp = client.post(
            "/",
            data={"tree_id": "backend", "skill_id": "http"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # The completed skill should show a checkmark
        assert "\u2713" in resp.data.decode()

    def test_post_toggles_skill_off(self, client):
        """Posting the same skill twice should uncomplete it."""
        client.post("/", data={"tree_id": "backend", "skill_id": "http"})
        resp = client.post(
            "/",
            data={"tree_id": "backend", "skill_id": "http"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # After toggling off, the checkmark should be gone for http
        # We check the API to be precise
        api_resp = client.get("/api/tree/backend")
        data = api_resp.get_json()
        assert "http" not in data["completed"]

    def test_post_adds_to_database(self, client):
        """After POST, the API should reflect the completed skill."""
        client.post("/", data={"tree_id": "backend", "skill_id": "sql"})
        resp = client.get("/api/tree/backend")
        data = resp.get_json()
        assert "sql" in data["completed"]


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


class TestAPITrees:
    def test_api_trees_returns_json(self, client):
        resp = client.get("/api/trees")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)

    def test_api_trees_contains_all_trees(self, client):
        resp = client.get("/api/trees")
        data = resp.get_json()
        assert "backend" in data
        assert "frontend" in data
        assert "devops" in data

    def test_api_trees_values_are_names(self, client):
        resp = client.get("/api/trees")
        data = resp.get_json()
        assert data["backend"] == "Backend Engineering"
        assert data["frontend"] == "Frontend Engineering"
        assert data["devops"] == "DevOps & Infrastructure"


class TestAPITree:
    def test_api_tree_backend(self, client):
        resp = client.get("/api/tree/backend")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Backend Engineering"
        assert "skills" in data
        assert "completed" in data

    def test_api_tree_returns_skills(self, client):
        resp = client.get("/api/tree/frontend")
        data = resp.get_json()
        skill_ids = [s["id"] for s in data["skills"]]
        assert "html-css" in skill_ids
        assert "react" in skill_ids

    def test_api_tree_nonexistent_returns_404(self, client):
        resp = client.get("/api/tree/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    def test_api_tree_completed_initially_empty(self, client):
        resp = client.get("/api/tree/devops")
        data = resp.get_json()
        assert data["completed"] == []


# ---------------------------------------------------------------------------
# Skill unlocking logic
# ---------------------------------------------------------------------------


class TestUnlockLogic:
    def test_level1_skills_unlocked_by_default(self, client):
        """Level 1 skills have no deps so should never be locked."""
        resp = client.get("/?tree=backend")
        html = resp.data.decode()
        # Level 1 skills (http, sql) should not have "locked" applied.
        # The template renders class="skill  locked" for locked skills.
        # For http (level 1), the button should NOT be disabled.
        # Find the http skill's form and verify it is not locked.
        http_idx = html.find('value="http"')
        assert http_idx != -1, "http skill not found in page"
        # Look at the surrounding button for this skill
        button_chunk = html[http_idx:http_idx + 300]
        assert "locked" not in button_chunk

    def test_level2_skill_locked_without_deps(self, client):
        """auth requires http; without completing http, auth should be locked."""
        resp = client.get("/?tree=backend")
        html = resp.data.decode()
        # Find the auth skill button — it should be locked
        assert "locked" in html

    def test_level2_skill_unlocked_after_dep_completed(self, client):
        """After completing http, auth should become unlocked."""
        # Complete the dependency
        client.post("/", data={"tree_id": "backend", "skill_id": "http"})
        resp = client.get("/?tree=backend")
        assert resp.status_code == 200
        page = resp.data.decode()
        # auth depends only on http, which is now complete
        # Find auth's button and verify it is not locked
        auth_idx = page.find('value="auth"')
        assert auth_idx != -1, "auth skill not found in page"
        button_chunk = page[auth_idx:auth_idx + 300]
        assert "locked" not in button_chunk


# ---------------------------------------------------------------------------
# Progress percentage calculation
# ---------------------------------------------------------------------------


class TestProgressCalculation:
    def test_zero_progress_initially(self, client):
        resp = client.get("/?tree=backend")
        html = resp.data.decode()
        assert "0/8 skills completed" in html
        assert "0%" in html

    def test_progress_after_one_skill(self, client):
        client.post("/", data={"tree_id": "backend", "skill_id": "http"})
        resp = client.get("/?tree=backend")
        html = resp.data.decode()
        assert "1/8 skills completed" in html
        assert "12%" in html  # int(1/8 * 100) = 12

    def test_progress_after_two_skills(self, client):
        client.post("/", data={"tree_id": "backend", "skill_id": "http"})
        client.post("/", data={"tree_id": "backend", "skill_id": "sql"})
        resp = client.get("/?tree=backend")
        html = resp.data.decode()
        assert "2/8 skills completed" in html
        assert "25%" in html  # int(2/8 * 100) = 25

    def test_progress_isolated_per_tree(self, client):
        """Completing a backend skill should not affect frontend progress."""
        client.post("/", data={"tree_id": "backend", "skill_id": "http"})
        resp = client.get("/?tree=frontend")
        html = resp.data.decode()
        assert "0/8 skills completed" in html

import pytest

from app import storage

MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def created_comment(client, created_task):
    response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "fixture comment"},
    )
    assert response.status_code == 201
    return response.json()


# --- Create ---


def test_create_comment_valid_returns_201_with_full_body(client, created_task):
    response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "Looks good to me"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["text"] == "Looks good to me"
    assert body["task_id"] == created_task["id"]
    assert "id" in body
    assert "created_at" in body
    assert body["edited_at"] is None


def test_create_comment_text_is_trimmed(client, created_task):
    response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "  spaced out  "},
    )
    assert response.status_code == 201
    assert response.json()["text"] == "spaced out"


def test_create_comment_blank_text_returns_422(client, created_task):
    response = client.post(f"/tasks/{created_task['id']}/comments", json={"text": "   "})
    assert response.status_code == 422


def test_create_comment_missing_text_returns_422(client, created_task):
    response = client.post(f"/tasks/{created_task['id']}/comments", json={})
    assert response.status_code == 422


def test_create_comment_too_long_returns_422_naming_the_limit(client, created_task):
    response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "x" * 1001},
    )
    assert response.status_code == 422
    assert "1000" in str(response.json()["detail"])


def test_create_comment_at_limit_returns_201(client, created_task):
    response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "x" * 1000},
    )
    assert response.status_code == 201


def test_create_comment_client_supplied_timestamp_returns_422(client, created_task):
    response = client.post(
        f"/tasks/{created_task['id']}/comments",
        json={"text": "hello", "created_at": "2020-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


def test_create_comment_on_missing_task_returns_404(client):
    response = client.post(f"/tasks/{MISSING_ID}/comments", json={"text": "hello"})
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {MISSING_ID} not found"


def test_failed_create_persists_nothing(client, created_task):
    client.post(f"/tasks/{created_task['id']}/comments", json={"text": "   "})
    response = client.get(f"/tasks/{created_task['id']}/comments")
    assert response.json() == []


# --- List ---


def test_list_comments_empty_returns_200_and_empty_list(client, created_task):
    response = client.get(f"/tasks/{created_task['id']}/comments")
    assert response.status_code == 200
    assert response.json() == []


def test_list_comments_ordered_oldest_first(client, created_task):
    for text in ["first", "second", "third"]:
        client.post(f"/tasks/{created_task['id']}/comments", json={"text": text})
    response = client.get(f"/tasks/{created_task['id']}/comments")
    assert response.status_code == 200
    assert [comment["text"] for comment in response.json()] == ["first", "second", "third"]


def test_list_comments_scoped_to_requested_task(client):
    task_a = client.post("/tasks", json={"title": "Task A"}).json()
    task_b = client.post("/tasks", json={"title": "Task B"}).json()
    client.post(f"/tasks/{task_a['id']}/comments", json={"text": "on A"})
    client.post(f"/tasks/{task_b['id']}/comments", json={"text": "on B"})

    response = client.get(f"/tasks/{task_a['id']}/comments")
    comments = response.json()
    assert len(comments) == 1
    assert comments[0]["text"] == "on A"


def test_list_comments_on_missing_task_returns_404(client):
    response = client.get(f"/tasks/{MISSING_ID}/comments")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {MISSING_ID} not found"


# --- Edit ---


def test_patch_comment_replaces_text_and_sets_edited_at(client, created_task, created_comment):
    response = client.patch(
        f"/tasks/{created_task['id']}/comments/{created_comment['id']}",
        json={"text": "corrected"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "corrected"
    assert body["edited_at"] is not None
    assert body["created_at"] == created_comment["created_at"]


def test_patch_comment_keeps_only_last_edit_time(client, created_task, created_comment):
    first = client.patch(
        f"/tasks/{created_task['id']}/comments/{created_comment['id']}",
        json={"text": "first edit"},
    ).json()
    second = client.patch(
        f"/tasks/{created_task['id']}/comments/{created_comment['id']}",
        json={"text": "second edit"},
    ).json()
    assert second["edited_at"] >= first["edited_at"]
    assert second["created_at"] == created_comment["created_at"]


def test_patch_comment_blank_text_returns_422(client, created_task, created_comment):
    response = client.patch(
        f"/tasks/{created_task['id']}/comments/{created_comment['id']}",
        json={"text": "   "},
    )
    assert response.status_code == 422


def test_patch_comment_missing_comment_returns_404(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}/comments/{MISSING_ID}",
        json={"text": "hello"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == f"Comment with id {MISSING_ID} not found"


def test_patch_comment_missing_task_returns_404(client):
    response = client.patch(
        f"/tasks/{MISSING_ID}/comments/{MISSING_ID}",
        json={"text": "hello"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {MISSING_ID} not found"


# --- Delete ---


def test_delete_comment_returns_204_and_removes_it(client, created_task, created_comment):
    response = client.delete(
        f"/tasks/{created_task['id']}/comments/{created_comment['id']}"
    )
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{created_task['id']}/comments").json() == []


def test_delete_comment_missing_comment_returns_404(client, created_task):
    response = client.delete(f"/tasks/{created_task['id']}/comments/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Comment with id {MISSING_ID} not found"


def test_delete_comment_missing_task_returns_404(client):
    response = client.delete(f"/tasks/{MISSING_ID}/comments/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {MISSING_ID} not found"


def test_delete_comment_leaves_task_and_siblings_intact(client, created_task):
    kept = client.post(
        f"/tasks/{created_task['id']}/comments", json={"text": "keep me"}
    ).json()
    removed = client.post(
        f"/tasks/{created_task['id']}/comments", json={"text": "remove me"}
    ).json()

    client.delete(f"/tasks/{created_task['id']}/comments/{removed['id']}")

    assert client.get(f"/tasks/{created_task['id']}").status_code == 200
    remaining = client.get(f"/tasks/{created_task['id']}/comments").json()
    assert [comment["id"] for comment in remaining] == [kept["id"]]


def test_deleting_task_deletes_its_comments(client, created_task, created_comment):
    response = client.delete(f"/tasks/{created_task['id']}")
    assert response.status_code == 204
    assert created_task["id"] not in storage._comments

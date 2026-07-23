def test_create_task_valid_returns_201_with_full_body(client):
    payload = {
        "title": "My Task",
        "description": "A description",
        "status": "ToDo",
        "priority": "High",
        "assignee": "alice",
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "My Task"
    assert body["description"] == "A description"
    assert body["status"] == "ToDo"
    assert body["priority"] == "High"
    assert body["assignee"] == "alice"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_create_task_missing_title_returns_422(client):
    response = client.post("/tasks", json={})
    assert response.status_code == 422


def test_create_task_blank_title_returns_422(client):
    response = client.post("/tasks", json={"title": "   "})
    assert response.status_code == 422


def test_create_task_invalid_priority_returns_422(client):
    response = client.post("/tasks", json={"title": "Valid title", "priority": "Urgent"})
    assert response.status_code == 422


def test_create_task_unknown_field_returns_422(client):
    response = client.post("/tasks", json={"title": "Valid title", "unknown": "value"})
    assert response.status_code == 422


def test_list_tasks_empty_returns_200_and_empty_list(client):
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_status_no_match_returns_200_and_empty_list(client):
    client.post("/tasks", json={"title": "Active task"})
    response = client.get("/tasks", params={"status": "Done"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_priority_returns_only_matches(client):
    client.post("/tasks", json={"title": "Low task", "priority": "Low"})
    client.post("/tasks", json={"title": "High task", "priority": "High"})
    response = client.get("/tasks", params={"priority": "High"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "High task"
    assert tasks[0]["priority"] == "High"


def test_list_tasks_search_matches_title_case_insensitively(client):
    client.post("/tasks", json={"title": "Deploy API"})
    client.post("/tasks", json={"title": "Write docs"})
    response = client.get("/tasks", params={"search": "deploy"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Deploy API"


def test_list_tasks_search_matches_partial_word_and_description(client):
    client.post("/tasks", json={"title": "Ship it", "description": "Deploy the API"})
    response = client.get("/tasks", params={"search": "depl"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_tasks_blank_search_returns_all_tasks(client):
    client.post("/tasks", json={"title": "First"})
    client.post("/tasks", json={"title": "Second"})
    response = client.get("/tasks", params={"search": "   "})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_tasks_search_no_match_returns_200_and_empty_list(client):
    client.post("/tasks", json={"title": "Deploy API"})
    response = client.get("/tasks", params={"search": "nonexistent"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_assignee_returns_only_matches(client):
    client.post("/tasks", json={"title": "Alice task", "assignee": "alice"})
    client.post("/tasks", json={"title": "Bob task", "assignee": "bob"})
    response = client.get("/tasks", params={"assignee": "alice"})
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["assignee"] == "alice"


def test_list_tasks_combined_filters_apply_as_and(client):
    client.post(
        "/tasks",
        json={"title": "Deploy API", "priority": "High", "assignee": "alice"},
    )
    client.post(
        "/tasks",
        json={"title": "Deploy frontend", "priority": "Low", "assignee": "alice"},
    )
    client.post(
        "/tasks",
        json={"title": "Deploy docs", "priority": "High", "assignee": "bob"},
    )

    response = client.get(
        "/tasks",
        params={
            "search": "deploy",
            "status": "ToDo",
            "priority": "High",
            "assignee": "alice",
        },
    )

    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Deploy API"


def test_list_tasks_no_filters_returns_all_tasks(client):
    client.post("/tasks", json={"title": "First"})
    client.post("/tasks", json={"title": "Second"})
    response = client.get("/tasks")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_tasks_unknown_query_parameter_returns_422(client):
    client.post("/tasks", json={"title": "Deploy API"})
    response = client.get("/tasks", params={"statuss": "Done"})
    assert response.status_code == 422


def test_list_tasks_empty_status_value_returns_422(client):
    response = client.get("/tasks", params={"status": ""})
    assert response.status_code == 422


def test_list_tasks_multiple_invalid_parameters_are_all_reported(client):
    response = client.get("/tasks", params={"status": "Nope", "priority": "Urgent"})
    assert response.status_code == 422
    reported = {error["loc"][-1] for error in response.json()["detail"]}
    assert reported == {"status", "priority"}


def test_get_task_by_id_returns_task(client, created_task):
    response = client.get(f"/tasks/{created_task['id']}")
    assert response.status_code == 200
    assert response.json() == created_task


def test_get_task_by_id_not_found_returns_404_with_detail(client):
    task_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {task_id} not found"


def test_patch_partial_update_keeps_other_fields(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"description": "updated description"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == created_task["title"]
    assert body["description"] == "updated description"
    assert body["status"] == created_task["status"]
    assert body["priority"] == created_task["priority"]
    assert body["assignee"] == created_task["assignee"]


def test_patch_not_found_returns_404(client):
    task_id = "00000000-0000-0000-0000-000000000000"
    response = client.patch(f"/tasks/{task_id}", json={"title": "New title"})
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {task_id} not found"


def test_patch_valid_transition_todo_to_inprogress_returns_200(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "InProgress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "InProgress"


def test_patch_invalid_transition_todo_to_done_returns_422(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "Done"},
    )
    assert response.status_code == 422


def test_patch_same_status_returns_200(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"status": "ToDo"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ToDo"


def test_patch_done_to_todo_returns_422_with_invalid_transition_detail(client):
    create_response = client.post(
        "/tasks",
        json={"title": "Completed task", "status": "Done"},
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "ToDo"},
    )

    assert response.status_code == 422
    assert "Invalid status transition" in response.json()["detail"]


def test_delete_existing_returns_204_no_body(client, created_task):
    response = client.delete(f"/tasks/{created_task['id']}")
    assert response.status_code == 204
    assert response.content == b""


def test_delete_missing_returns_404(client):
    task_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == f"Task with id {task_id} not found"

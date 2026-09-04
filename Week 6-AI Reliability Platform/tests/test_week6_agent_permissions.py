"""Week 6 — verifies the live agent tool path (not just the evaluation
harness) actually enforces the L0-L4 approval gate on delete_task and
send_email_summary."""
from app.services.agent_service import build_meeting_tools
from app.models.models import AgentTask, db


def test_delete_task_refuses_without_approval(app):
    with app.app_context():
        from tests.conftest import register
        # Minimal user row for the FK — reuse conftest's register helper via a raw insert
        from app.models.models import User
        user = User(username="deltest", email="deltest@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        task = AgentTask(user_id=user.id, agent_key="meeting", title="Do not delete me")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        tools = build_meeting_tools(user.id, user.email, "meeting", approved_tools=set())
        delete_fn = next(t for t in tools if t.__name__ == "delete_task")
        result = delete_fn(task_id)

        assert "confirmation" in result.lower() or "confirm" in result.lower()
        assert AgentTask.query.get(task_id) is not None  # NOT deleted


def test_delete_task_succeeds_with_approval(app):
    with app.app_context():
        from app.models.models import User
        user = User(username="deltest2", email="deltest2@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        task = AgentTask(user_id=user.id, agent_key="meeting", title="OK to delete")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

        tools = build_meeting_tools(user.id, user.email, "meeting", approved_tools={"delete_task"})
        delete_fn = next(t for t in tools if t.__name__ == "delete_task")
        result = delete_fn(task_id)

        assert "deleted" in result.lower()
        assert AgentTask.query.get(task_id) is None


def test_create_task_does_not_require_approval(app):
    with app.app_context():
        from app.models.models import User
        user = User(username="deltest3", email="deltest3@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        tools = build_meeting_tools(user.id, user.email, "meeting", approved_tools=set())
        create_fn = next(t for t in tools if t.__name__ == "create_task")
        result = create_fn("A normal low-risk task")
        assert "created task" in result.lower()


def test_email_summary_refuses_without_approval(app, monkeypatch):
    with app.app_context():
        from app.models.models import User
        user = User(username="deltest4", email="deltest4@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        tools = build_meeting_tools(user.id, user.email, "meeting", approved_tools=set())
        email_fn = next(t for t in tools if t.__name__ == "send_email_summary")
        result = email_fn("Subject", "Body")
        assert "confirm" in result.lower()

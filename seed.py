"""
Creates the tables (if missing) and inserts one demo Owner + Widget with a
fixed, known ID so you can curl the submission endpoint immediately without
needing the (Phase 3) auth/widget-management API first.

Run:  python seed.py
"""
from app.db import Base, engine, SessionLocal
from app.models import Owner, Widget

DEMO_OWNER_ID = "00000000-0000-0000-0000-000000000001"
DEMO_WIDGET_ID = "00000000-0000-0000-0000-0000000000aa"


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.get(Owner, DEMO_OWNER_ID):
            db.add(
                Owner(
                    id=DEMO_OWNER_ID,
                    email="demo-owner@example.com",
                    password_hash="not-a-real-hash-phase3-adds-auth",
                )
            )
        if not db.get(Widget, DEMO_WIDGET_ID):
            db.add(
                Widget(
                    id=DEMO_WIDGET_ID,
                    owner_id=DEMO_OWNER_ID,
                    type="signup_form",
                    title="Demo signup widget",
                    description="Seeded for Phase 2 curl testing.",
                    fields=[
                        {"name": "email", "label": "Email", "type": "email", "required": True},
                    ],
                    button_text="Sign up",
                )
            )
        db.commit()
    finally:
        db.close()

    print("Seed complete.")
    print(f"  demo widget_id = {DEMO_WIDGET_ID}")
    print()
    print("Try it:")
    print(
        "  curl -i -X POST http://localhost:8000/submissions "
        "-H 'Content-Type: application/json' "
        f"-H 'Origin: http://localhost:5500' "
        f'-d \'{{"widget_id": "{DEMO_WIDGET_ID}", "fields": {{"email": "visitor@example.com"}}}}\''
    )


if __name__ == "__main__":
    run()

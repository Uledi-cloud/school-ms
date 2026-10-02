# reset_online_dev.py
# Reset/create the developer account on the ONLINE database.
import os
import sys

# Ask for the DATABASE_URL
db_url = input("Paste your Railway DATABASE_URL here, then press Enter:\n> ").strip()

if not db_url:
    print("No URL provided. Exiting.")
    sys.exit(1)

# Force SQLAlchemy to use it
os.environ['DATABASE_URL'] = db_url

# Import AFTER setting env so the app picks up the URL
from app import app
from models import db, User, School

with app.app_context():
    db.create_all()

    print("\n=== BEFORE ===")
    users = User.query.all()
    print(f"Total users in online DB: {len(users)}")
    for u in users:
        print(f"  - username={u.username}, role={u.role}, active={u.is_active_flag}")

    existing = User.query.filter_by(role='developer').first()

    if existing:
        existing.set_password('Dev@12345')
        existing.is_active_flag = True
        existing.must_change_password = False
        db.session.commit()
        print("\n=== RESET ===")
        print(f"Developer account reset: {existing.username} / Dev@12345")
    else:
        dev = User(
            username='developer',
            email='dev@school.com',
            full_name='System Developer',
            role='developer',
            is_active_flag=True,
            must_change_password=False,
        )
        dev.set_password('Dev@12345')
        db.session.add(dev)
        db.session.commit()
        print("\n=== CREATED ===")
        print("Developer account created: developer / Dev@12345")

    print("\n=== ALL USERS AFTER ===")
    for u in User.query.all():
        print(f"  - username={u.username}, role={u.role}, active={u.is_active_flag}")

    print("\n=== SCHOOLS ===")
    for s in School.query.all():
        print(f"  - ID={s.id} | name={s.name} | active={s.is_active}")

print("\nDone. Now log in at /login with developer / Dev@12345")

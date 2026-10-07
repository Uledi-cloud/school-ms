# reset_dev_pwd.py
import os, sys

db_url = input("Paste Railway DATABASE_URL:\n> ").strip().strip('"').strip("'")

for prefix in ("DATABASE_URL=", "url = "):
    if db_url.startswith(prefix):
        db_url = db_url[len(prefix):].strip()

if db_url.startswith("postgres://"):
    db_url = "postgresql://" + db_url[len("postgres://"):]

if not db_url.startswith("postgresql://"):
    print(f"ERROR: URL must start with postgresql:// - got: {db_url[:50]}")
    sys.exit(1)

print(f"Connecting to: {db_url[:40]}...")
os.environ['DATABASE_URL'] = db_url

from app import app
from models import db, User

with app.app_context():
    db.create_all()

    users = User.query.all()
    print(f"\n=== Users in online DB: {len(users)} ===")
    for u in users:
        print(f"  username={u.username} | role={u.role} | active={u.is_active_flag}")

    existing = User.query.filter_by(role='developer').first()
    if existing:
        existing.set_password('Dev@12345')
        existing.is_active_flag = True
        existing.must_change_password = False
        db.session.commit()
        print(f"\n=== RESET ===")
        print(f"Username: {existing.username}")
        print(f"Password: Dev@12345")
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
        print("Username: developer")
        print("Password: Dev@12345")

print("\nNow log in at /login with: developer / Dev@12345")

# bootstrap_dev.py — Auto-creates developer user on app startup
def ensure_developer_exists(app, db, User, generate_password_hash):
    with app.app_context():
        try:
            dev = User.query.filter_by(username="developer").first()
            if not dev:
                dev = User(
                    username="developer",
                    email="developer@system.local",
                    role="developer",
                    school_id=None,
                    is_active_flag=True
                )
                dev.password_hash = generate_password_hash("Dev'12345")
                db.session.add(dev)
                db.session.commit()
                print(">>> BOOTSTRAP: Developer user created.")
            else:
                dev.password_hash = generate_password_hash("Dev'12345")
                dev.role = "developer"
                dev.school_id = None
                dev.is_active_flag = True
                db.session.commit()
                print(">>> BOOTSTRAP: Developer user refreshed.")
        except Exception as e:
            print(f">>> BOOTSTRAP ERROR: {e}")
            db.session.rollback()

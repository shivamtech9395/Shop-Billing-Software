"""
Emergency admin recovery script.
Run this from the backend folder if you ever get locked out:

    python fix_admin.py

It will:
1. Reactivate every admin account that was deactivated
2. Let you set a new password for any user if you want
"""
from database import SessionLocal, User
from auth import hash_password

db = SessionLocal()

print("=== Reactivating all admin accounts ===")
admins = db.query(User).filter(User.role == "admin").all()
if not admins:
    print("No admin account found at all! Something is wrong with the database.")
else:
    for admin in admins:
        admin.is_active = True
        print(f"Reactivated: {admin.username} ({admin.name})")
    db.commit()

print("\n=== All users in the system ===")
users = db.query(User).all()
for u in users:
    status = "active" if u.is_active else "DEACTIVATED"
    print(f"  id={u.id}  username={u.username}  role={u.role}  status={status}")

print("\nDo you also want to reset a password? (y/n)")
choice = input("> ").strip().lower()
if choice == "y":
    username = input("Enter the username to reset: ").strip()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        print("No such username found.")
    else:
        new_password = input("Enter the new password: ").strip()
        user.password_hash = hash_password(new_password)
        user.is_active = True
        db.commit()
        print(f"Password updated for '{username}'. You can log in now.")

db.close()
print("\nDone. Try logging in again.")
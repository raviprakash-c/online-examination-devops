import os
import sys

from werkzeug.security import generate_password_hash

from .db import get_connection


def main():
    username = os.getenv("ADMIN_USERNAME")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    missing = [
        name for name, value in {
            "ADMIN_USERNAME": username,
            "ADMIN_EMAIL": email,
            "ADMIN_PASSWORD": password,
        }.items() if not value
    ]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        return 2

    if len(password) < 8:
        print("ADMIN_PASSWORD must contain at least 8 characters")
        return 2

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email.lower().strip(),),
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE users
                    SET username = %s,
                        password_hash = %s,
                        role = 'admin'
                    WHERE id = %s
                    """,
                    (
                        username.strip(),
                        generate_password_hash(password),
                        existing["id"],
                    ),
                )
                action = "updated"
                user_id = existing["id"]
            else:
                cursor.execute(
                    """
                    INSERT INTO users
                        (username, email, password_hash, role)
                    VALUES (%s, %s, %s, 'admin')
                    """,
                    (
                        username.strip(),
                        email.lower().strip(),
                        generate_password_hash(password),
                    ),
                )
                action = "created"
                user_id = cursor.lastrowid

        connection.commit()
        print("Admin " + action + " successfully. id=" + str(user_id))
        return 0
    except Exception as exc:
        connection.rollback()
        print("Unable to provision admin: " + str(exc))
        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())

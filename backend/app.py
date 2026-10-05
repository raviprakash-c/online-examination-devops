import os
from functools import wraps

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from .db import get_connection
except ImportError:
    from db import get_connection


app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_COOKIE_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
)

CORS(app, supports_credentials=True)


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def fetch_one(query, params=()):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    finally:
        connection.close()


def fetch_all(query, params=()):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        connection.close()


def execute_query(query, params=()):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            result = {
                "lastrowid": cursor.lastrowid,
                "rowcount": cursor.rowcount,
            }
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        user = fetch_one(
            "SELECT id, username, email, role FROM users WHERE id = %s",
            (user_id,),
        )
        if not user:
            session.clear()
            return jsonify({"error": "User session is no longer valid"}), 401

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        user = fetch_one(
            "SELECT id, username, email, role FROM users WHERE id = %s",
            (user_id,),
        )
        if not user:
            session.clear()
            return jsonify({"error": "User session is no longer valid"}), 401

        if user["role"] != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return view(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    return fetch_one(
        "SELECT id, username, email, role, created_at FROM users WHERE id = %s",
        (user_id,),
    )


def validate_exam_payload(data):
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    try:
        duration = int(data.get("duration_minutes", 0))
    except (TypeError, ValueError):
        duration = 0

    if not title:
        return None, "Exam title is required"
    if duration <= 0 or duration > 600:
        return None, "duration_minutes must be between 1 and 600"

    return {
        "title": title,
        "description": description or None,
        "duration_minutes": duration,
    }, None


def validate_question_payload(data):
    question_text = str(data.get("question_text", "")).strip()
    options = {
        "option_a": str(data.get("option_a", "")).strip(),
        "option_b": str(data.get("option_b", "")).strip(),
        "option_c": str(data.get("option_c", "")).strip(),
        "option_d": str(data.get("option_d", "")).strip(),
    }
    correct_option = str(data.get("correct_option", "")).strip().lower()

    try:
        marks = int(data.get("marks", 1))
    except (TypeError, ValueError):
        marks = 0

    if not question_text:
        return None, "question_text is required"
    if any(not value for value in options.values()):
        return None, "All four options are required"
    if correct_option not in {"a", "b", "c", "d"}:
        return None, "correct_option must be a, b, c, or d"
    if marks <= 0 or marks > 100:
        return None, "marks must be between 1 and 100"

    return {
        "question_text": question_text,
        **options,
        "correct_option": correct_option,
        "marks": marks,
    }, None


@app.get("/")
def home():
    return jsonify({
        "message": "Online Examination System API",
        "status": "running",
        "version": "1.0.0",
    })


@app.get("/api/health")
def health():
    try:
        result = fetch_one("SELECT 1 AS result")
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "result": result,
        })
    except Exception:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
        }), 503


# -------------------- Authentication --------------------

@app.post("/api/auth/register")
def register():
    data = json_body()
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if len(username) < 3:
        return jsonify({"error": "Username must contain at least 3 characters"}), 400
    if "@" not in email or "." not in email:
        return jsonify({"error": "A valid email address is required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must contain at least 8 characters"}), 400

    try:
        result = execute_query(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, 'student')
            """,
            (username, email, generate_password_hash(password)),
        )
        return jsonify({
            "message": "Registration successful",
            "user": {
                "id": result["lastrowid"],
                "username": username,
                "email": email,
                "role": "student",
            },
        }), 201
    except Exception as exc:
        error_text = str(exc).lower()
        if "duplicate" in error_text or "unique" in error_text:
            return jsonify({"error": "Username or email already exists"}), 409
        return jsonify({"error": "Unable to create user"}), 500


@app.post("/api/auth/login")
def login():
    data = json_body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = fetch_one(
        """
        SELECT id, username, email, password_hash, role
        FROM users
        WHERE email = %s
        """,
        (email,),
    )

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.clear()
    session["user_id"] = user["id"]

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
        },
    })


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logout successful"})


@app.get("/api/auth/me")
@login_required
def me():
    user = current_user()
    return jsonify({"user": user})


# -------------------- Exams --------------------

@app.get("/api/exams")
@login_required
def list_exams():
    user = current_user()

    if user["role"] == "admin":
        exams = fetch_all(
            """
            SELECT id, title, description, duration_minutes, created_at
            FROM exams
            ORDER BY created_at DESC
            """
        )
    else:
        exams = fetch_all(
            """
            SELECT id, title, description, duration_minutes, created_at
            FROM exams
            ORDER BY created_at DESC
            """
        )

    return jsonify({"exams": exams})


@app.post("/api/exams")
@admin_required
def create_exam():
    data = json_body()
    payload, error = validate_exam_payload(data)
    if error:
        return jsonify({"error": error}), 400

    result = execute_query(
        """
        INSERT INTO exams (title, description, duration_minutes)
        VALUES (%s, %s, %s)
        """,
        (payload["title"], payload["description"], payload["duration_minutes"]),
    )

    exam = fetch_one(
        """
        SELECT id, title, description, duration_minutes, created_at
        FROM exams
        WHERE id = %s
        """,
        (result["lastrowid"],),
    )

    return jsonify({"message": "Exam created", "exam": exam}), 201


@app.put("/api/exams/<int:exam_id>")
@admin_required
def update_exam(exam_id):
    data = json_body()
    payload, error = validate_exam_payload(data)
    if error:
        return jsonify({"error": error}), 400

    existing = fetch_one("SELECT id FROM exams WHERE id = %s", (exam_id,))
    if not existing:
        return jsonify({"error": "Exam not found"}), 404

    execute_query(
        """
        UPDATE exams
        SET title = %s, description = %s, duration_minutes = %s
        WHERE id = %s
        """,
        (
            payload["title"],
            payload["description"],
            payload["duration_minutes"],
            exam_id,
        ),
    )

    exam = fetch_one(
        """
        SELECT id, title, description, duration_minutes, created_at
        FROM exams
        WHERE id = %s
        """,
        (exam_id,),
    )
    return jsonify({"message": "Exam updated", "exam": exam})


@app.delete("/api/exams/<int:exam_id>")
@admin_required
def delete_exam(exam_id):
    existing = fetch_one("SELECT id FROM exams WHERE id = %s", (exam_id,))
    if not existing:
        return jsonify({"error": "Exam not found"}), 404

    execute_query("DELETE FROM exams WHERE id = %s", (exam_id,))
    return jsonify({"message": "Exam deleted"})


# -------------------- Questions --------------------

@app.get("/api/exams/<int:exam_id>/questions")
@login_required
def list_questions(exam_id):
    exam = fetch_one("SELECT id FROM exams WHERE id = %s", (exam_id,))
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    user = current_user()
    if user["role"] == "admin":
        questions = fetch_all(
            """
            SELECT id, exam_id, question_text, option_a, option_b,
                   option_c, option_d, correct_option, marks
            FROM questions
            WHERE exam_id = %s
            ORDER BY id
            """,
            (exam_id,),
        )
    else:
        questions = fetch_all(
            """
            SELECT id, exam_id, question_text, option_a, option_b,
                   option_c, option_d, marks
            FROM questions
            WHERE exam_id = %s
            ORDER BY id
            """,
            (exam_id,),
        )

    return jsonify({"questions": questions})


@app.post("/api/exams/<int:exam_id>/questions")
@admin_required
def create_question(exam_id):
    exam = fetch_one("SELECT id FROM exams WHERE id = %s", (exam_id,))
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    payload, error = validate_question_payload(json_body())
    if error:
        return jsonify({"error": error}), 400

    result = execute_query(
        """
        INSERT INTO questions
            (exam_id, question_text, option_a, option_b, option_c,
             option_d, correct_option, marks)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            exam_id,
            payload["question_text"],
            payload["option_a"],
            payload["option_b"],
            payload["option_c"],
            payload["option_d"],
            payload["correct_option"],
            payload["marks"],
        ),
    )

    question = fetch_one(
        """
        SELECT id, exam_id, question_text, option_a, option_b,
               option_c, option_d, correct_option, marks
        FROM questions
        WHERE id = %s
        """,
        (result["lastrowid"],),
    )
    return jsonify({"message": "Question created", "question": question}), 201


@app.put("/api/exams/<int:exam_id>/questions/<int:question_id>")
@admin_required
def update_question(exam_id, question_id):
    existing = fetch_one(
        "SELECT id FROM questions WHERE id = %s AND exam_id = %s",
        (question_id, exam_id),
    )
    if not existing:
        return jsonify({"error": "Question not found"}), 404

    payload, error = validate_question_payload(json_body())
    if error:
        return jsonify({"error": error}), 400

    execute_query(
        """
        UPDATE questions
        SET question_text = %s,
            option_a = %s,
            option_b = %s,
            option_c = %s,
            option_d = %s,
            correct_option = %s,
            marks = %s
        WHERE id = %s AND exam_id = %s
        """,
        (
            payload["question_text"],
            payload["option_a"],
            payload["option_b"],
            payload["option_c"],
            payload["option_d"],
            payload["correct_option"],
            payload["marks"],
            question_id,
            exam_id,
        ),
    )

    question = fetch_one(
        """
        SELECT id, exam_id, question_text, option_a, option_b,
               option_c, option_d, correct_option, marks
        FROM questions
        WHERE id = %s
        """,
        (question_id,),
    )
    return jsonify({"message": "Question updated", "question": question})


@app.delete("/api/exams/<int:exam_id>/questions/<int:question_id>")
@admin_required
def delete_question(exam_id, question_id):
    existing = fetch_one(
        "SELECT id FROM questions WHERE id = %s AND exam_id = %s",
        (question_id, exam_id),
    )
    if not existing:
        return jsonify({"error": "Question not found"}), 404

    execute_query(
        "DELETE FROM questions WHERE id = %s AND exam_id = %s",
        (question_id, exam_id),
    )
    return jsonify({"message": "Question deleted"})


# -------------------- Exam Attempts --------------------

@app.post("/api/exams/<int:exam_id>/start")
@login_required
def start_exam(exam_id):
    user = current_user()
    if user["role"] != "student":
        return jsonify({"error": "Only students can start an exam"}), 403

    exam = fetch_one(
        """
        SELECT id, title, description, duration_minutes
        FROM exams
        WHERE id = %s
        """,
        (exam_id,),
    )
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    active_attempt = fetch_one(
        """
        SELECT id, started_at
        FROM attempts
        WHERE user_id = %s AND exam_id = %s AND submitted_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (user["id"], exam_id),
    )

    if active_attempt:
        attempt_id = active_attempt["id"]
        started_at = active_attempt["started_at"]
    else:
        result = execute_query(
            """
            INSERT INTO attempts (user_id, exam_id)
            VALUES (%s, %s)
            """,
            (user["id"], exam_id),
        )
        attempt_id = result["lastrowid"]
        attempt = fetch_one(
            "SELECT started_at FROM attempts WHERE id = %s",
            (attempt_id,),
        )
        started_at = attempt["started_at"]

    questions = fetch_all(
        """
        SELECT id, exam_id, question_text, option_a, option_b,
               option_c, option_d, marks
        FROM questions
        WHERE exam_id = %s
        ORDER BY id
        """,
        (exam_id,),
    )

    return jsonify({
        "message": "Exam started",
        "attempt": {
            "id": attempt_id,
            "exam_id": exam_id,
            "started_at": started_at,
            "duration_minutes": exam["duration_minutes"],
        },
        "exam": exam,
        "questions": questions,
    })


@app.get("/api/attempts/<int:attempt_id>")
@login_required
def get_attempt(attempt_id):
    user = current_user()
    attempt = fetch_one(
        """
        SELECT a.id, a.user_id, a.exam_id, a.started_at,
               a.submitted_at, a.score,
               e.title, e.duration_minutes
        FROM attempts a
        JOIN exams e ON e.id = a.exam_id
        WHERE a.id = %s
        """,
        (attempt_id,),
    )

    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    if user["role"] != "admin" and attempt["user_id"] != user["id"]:
        return jsonify({"error": "Access denied"}), 403

    answers = fetch_all(
        """
        SELECT answer_id, question_id, selected_option, is_correct
        FROM (
            SELECT id AS answer_id, question_id, selected_option, is_correct
            FROM answers
            WHERE attempt_id = %s
        ) AS attempt_answers
        ORDER BY question_id
        """,
        (attempt_id,),
    )

    return jsonify({"attempt": attempt, "answers": answers})


@app.post("/api/attempts/<int:attempt_id>/submit")
@login_required
def submit_attempt(attempt_id):
    user = current_user()
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.id, a.user_id, a.exam_id, a.started_at,
                       a.submitted_at, e.duration_minutes
                FROM attempts a
                JOIN exams e ON e.id = a.exam_id
                WHERE a.id = %s
                FOR UPDATE
                """,
                (attempt_id,),
            )
            attempt = cursor.fetchone()

            if not attempt:
                connection.rollback()
                return jsonify({"error": "Attempt not found"}), 404

            if user["role"] != "admin" and attempt["user_id"] != user["id"]:
                connection.rollback()
                return jsonify({"error": "Access denied"}), 403

            if attempt["submitted_at"] is not None:
                connection.rollback()
                result = fetch_one(
                    """
                    SELECT id, exam_id, submitted_at, score
                    FROM attempts
                    WHERE id = %s
                    """,
                    (attempt_id,),
                )
                return jsonify({
                    "message": "Attempt already submitted",
                    "result": result,
                })

            cursor.execute(
                """
                SELECT id, correct_option, marks
                FROM questions
                WHERE exam_id = %s
                """,
                (attempt["exam_id"],),
            )
            questions = cursor.fetchall()

            payload = json_body()
            raw_answers = payload.get("answers", [])
            if not isinstance(raw_answers, list):
                connection.rollback()
                return jsonify({"error": "answers must be a list"}), 400

            submitted_answers = {}
            for item in raw_answers:
                if not isinstance(item, dict):
                    continue
                try:
                    question_id = int(item.get("question_id"))
                except (TypeError, ValueError):
                    continue

                option = str(item.get("selected_option", "")).strip().lower()
                submitted_answers[question_id] = option if option in {"a", "b", "c", "d"} else None

            cursor.execute(
                "DELETE FROM answers WHERE attempt_id = %s",
                (attempt_id,),
            )

            score = 0
            total_marks = 0

            for question in questions:
                total_marks += question["marks"]
                selected_option = submitted_answers.get(question["id"])
                is_correct = selected_option == question["correct_option"]
                if is_correct:
                    score += question["marks"]

                cursor.execute(
                    """
                    INSERT INTO answers
                        (attempt_id, question_id, selected_option, is_correct)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        attempt_id,
                        question["id"],
                        selected_option,
                        is_correct,
                    ),
                )

            cursor.execute(
                """
                SELECT TIMESTAMPDIFF(SECOND, started_at, CURRENT_TIMESTAMP()) AS elapsed_seconds
                FROM attempts
                WHERE id = %s
                """,
                (attempt_id,),
            )
            timing = cursor.fetchone()
            elapsed_seconds = int(timing["elapsed_seconds"] or 0)
            time_limit_seconds = int(attempt["duration_minutes"]) * 60
            expired = elapsed_seconds > time_limit_seconds

            percentage = round((score / total_marks) * 100, 2) if total_marks else 0.0
            status = "PASS" if percentage >= 40 else "FAIL"

            cursor.execute(
                """
                UPDATE attempts
                SET submitted_at = CURRENT_TIMESTAMP(), score = %s
                WHERE id = %s
                """,
                (score, attempt_id),
            )

        connection.commit()

        return jsonify({
            "message": "Exam submitted successfully",
            "result": {
                "attempt_id": attempt_id,
                "exam_id": attempt["exam_id"],
                "score": score,
                "total_marks": total_marks,
                "percentage": percentage,
                "status": status,
                "expired": expired,
                "time_limit_seconds": time_limit_seconds,
                "elapsed_seconds": elapsed_seconds,
            },
        })
    except Exception:
        connection.rollback()
        return jsonify({"error": "Unable to submit exam"}), 500
    finally:
        connection.close()


# -------------------- Results --------------------

@app.get("/api/results")
@login_required
def student_results():
    user = current_user()
    results = fetch_all(
        """
        SELECT a.id AS attempt_id,
               e.id AS exam_id,
               e.title,
               e.duration_minutes,
               a.started_at,
               a.submitted_at,
               a.score,
               COALESCE(SUM(q.marks), 0) AS total_marks
        FROM attempts a
        JOIN exams e ON e.id = a.exam_id
        LEFT JOIN questions q ON q.exam_id = e.id
        WHERE a.user_id = %s
          AND a.submitted_at IS NOT NULL
        GROUP BY a.id, e.id, e.title, e.duration_minutes,
                 a.started_at, a.submitted_at, a.score
        ORDER BY a.submitted_at DESC
        """,
        (user["id"],),
    )

    for result in results:
        total_marks = float(result["total_marks"] or 0)
        score = float(result["score"] or 0)
        result["percentage"] = round((score / total_marks) * 100, 2) if total_marks else 0.0
        result["status"] = "PASS" if result["percentage"] >= 40 else "FAIL"

    return jsonify({"results": results})


@app.get("/api/admin/results")
@admin_required
def admin_results():
    results = fetch_all(
        """
        SELECT a.id AS attempt_id,
               u.id AS user_id,
               u.username,
               u.email,
               e.id AS exam_id,
               e.title,
               e.duration_minutes,
               a.started_at,
               a.submitted_at,
               a.score,
               COALESCE(SUM(q.marks), 0) AS total_marks
        FROM attempts a
        JOIN users u ON u.id = a.user_id
        JOIN exams e ON e.id = a.exam_id
        LEFT JOIN questions q ON q.exam_id = e.id
        WHERE a.submitted_at IS NOT NULL
        GROUP BY a.id, u.id, u.username, u.email, e.id, e.title,
                 e.duration_minutes, a.started_at, a.submitted_at, a.score
        ORDER BY a.submitted_at DESC
        """
    )

    for result in results:
        total_marks = float(result["total_marks"] or 0)
        score = float(result["score"] or 0)
        result["percentage"] = round((score / total_marks) * 100, 2) if total_marks else 0.0
        result["status"] = "PASS" if result["percentage"] >= 40 else "FAIL"

    return jsonify({"results": results})


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_error):
    return jsonify({"error": "HTTP method not allowed"}), 405


@app.errorhandler(500)
def server_error(_error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug)

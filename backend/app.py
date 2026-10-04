from flask import Flask, jsonify
from flask_cors import CORS

from db import get_connection

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({
        "message": "Online Examination System API",
        "status": "running"
    })


@app.route("/api/health")
def health():
    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS result")
            result = cursor.fetchone()

        connection.close()

        return jsonify({
            "status": "healthy",
            "database": "connected",
            "result": result
        })

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
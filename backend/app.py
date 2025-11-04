from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from jsonschema import validate, ValidationError

app = Flask(__name__)
CORS(app)

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESERVATIONS_FILE = os.path.join(BASE_DIR, "reservations.json")
SCHEMA_FILE = os.path.join(BASE_DIR, "reservation.json")

# Load reservations
if os.path.exists(RESERVATIONS_FILE):
    with open(RESERVATIONS_FILE, "r") as f:
        try:
            reservations = json.load(f)
        except json.JSONDecodeError:
            reservations = []
else:
    reservations = []

# Load schema
with open(SCHEMA_FILE, "r") as f:
    reservation_schema = json.load(f)

# 🟢 GET - All reservations
@app.route("/reservations", methods=["GET"])
def get_reservations():
    return jsonify(reservations), 200

# 🟢 POST - Add a reservation
@app.route("/reservations", methods=["POST"])
def add_reservation():
    data = request.get_json()
    print("📩 Received POST data:", data)

    # --- Data normalization ---
    try:
        data["guests"] = int(data["guests"])
    except (ValueError, TypeError):
        return jsonify({"error": "Guests must be an integer"}), 400

    # Resort ID (auto or placeholder)
    if "resort_id" not in data:
        data["resort_id"] = 1

    # Contact structure
    data["contact"] = {
        "phone": data.pop("phone", ""),
        "email": data.pop("email", "")
    }

    # Add timestamps
    now = datetime.now().isoformat() + "Z"
    data["created_at"] = now
    data["updated_at"] = now

    # Validate against JSON schema
    try:
        validate(instance=data, schema=reservation_schema)
    except ValidationError as e:
        print("❌ Schema Validation Error:", e.message)
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    # Add unique ID
    data["id"] = len(reservations) + 1

    # Save to file
    reservations.append(data)
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201


if __name__ == "__main__":
    app.run(debug=True)

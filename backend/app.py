from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from jsonschema import validate, ValidationError

app = Flask(__name__)
CORS(app)

# === File paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESERVATIONS_FILE = os.path.join(BASE_DIR, "reservations.json")
SCHEMA_FILE = os.path.join(BASE_DIR, "reservation.json")

# === Load existing reservations ===
if os.path.exists(RESERVATIONS_FILE):
    with open(RESERVATIONS_FILE, "r") as f:
        try:
            reservations = json.load(f)
        except json.JSONDecodeError:
            reservations = []
else:
    reservations = []

# === Load JSON Schema ===
with open(SCHEMA_FILE, "r") as f:
    reservation = json.load(f)

# === GET: All reservations ===
@app.route("/reservations", methods=["GET"])
def get_reservations():
    return jsonify(reservations), 200

# === POST: Add reservation ===
@app.route("/reservations", methods=["POST"])
def add_reservation():
    data = request.get_json()
    print("📩 Received POST data:", data)

    # --- Normalize / adjust frontend data ---
    # Wrap contact info (required by schema)
    contact_info = {
        "phone": data.get("phone", ""),
        "email": data.get("email", "")
    }
    data["contact"] = contact_info
    data.pop("phone", None)
    data.pop("email", None)

    # Resort mapping (frontend uses resort_name, schema uses resort_id)
    if "resort_name" in data:
        if data["resort_name"] == "Arcadia Beach Resort":
            data["resort_id"] = 1
        elif data["resort_name"] == "Kuya Boy Beach Resort":
            data["resort_id"] = 2
        else:
            data["resort_id"] = 0
        del data["resort_name"]

    # Convert guests to int
    try:
        data["guests"] = int(data.get("guests", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Guests must be an integer"}), 400

    # Auto ID + timestamps
    data["id"] = len(reservations) + 1
    now = datetime.utcnow().isoformat() + "Z"
    data["created_at"] = now
    data["updated_at"] = now

    # Default payment_status
    if "payment_status" not in data:
        data["payment_status"] = "pending"

    # --- Validate using schema ---
    try:
        validate(instance=data, schema=reservation)
    except ValidationError as e:
        print("❌ Schema Validation Error:", e.message)
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    # --- Save ---
    reservations.append(data)
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201

# === PUT: Update ===
@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    existing = next((r for r in reservations if r["id"] == res_id), None)
    if not existing:
        return jsonify({"error": "Reservation not found"}), 404

    updated = request.get_json()
    print(f"✏️ Updating reservation ID {res_id}:", updated)

    existing.update(updated)
    existing["updated_at"] = datetime.utcnow().isoformat() + "Z"

    try:
        validate(instance=existing, schema=reservation)
    except ValidationError as e:
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": "Reservation updated successfully!", "data": existing}), 200

# === DELETE: Remove ===
@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    global reservations
    filtered = [r for r in reservations if r["id"] != res_id]
    if len(filtered) == len(reservations):
        return jsonify({"error": "Reservation not found"}), 404

    reservations = filtered
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": f"Reservation {res_id} deleted successfully!"}), 200

if __name__ == "__main__":
    app.run(debug=True)

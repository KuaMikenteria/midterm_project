from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from jsonschema import validate, ValidationError

app = Flask(__name__)
CORS(app)

# === Base paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESERVATIONS_FILE = os.path.join(BASE_DIR, "reservations.json")
SCHEMA_FILE = os.path.join(BASE_DIR, "reservation.json")

# === Load reservations ===
if os.path.exists(RESERVATIONS_FILE):
    with open(RESERVATIONS_FILE, "r") as f:
        try:
            reservations = json.load(f)
        except json.JSONDecodeError:
            reservations = []
else:
    reservations = []

# === Load schema ===
with open(SCHEMA_FILE, "r") as f:
    reservation_schema = json.load(f)


# === Helper Function ===
def save_reservations():
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)


# === GET /reservations ===
@app.route("/reservations", methods=["GET"])
def get_reservations():
    return jsonify(reservations), 200


# === POST /reservations ===
@app.route("/reservations", methods=["POST"])
def add_reservation():
    data = request.get_json()
    print("📩 Received POST data:", data)

    # Normalize types
    try:
        data["guests"] = int(data.get("guests", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "Guests must be an integer"}), 400

    # Ensure resort_id exists
    if "resort_id" not in data:
        data["resort_id"] = 1

    # --- Combine address fields ---
    data["address"] = f"{data.get('street_address', '')}, {data.get('municipality', '')}, {data.get('region', '')}, {data.get('country', '')}"

    # --- Ensure contact object ---
    data["contact"] = {
        "phone": data.pop("phone", ""),
        "email": data.pop("email", "")
    }

    # --- Ensure valid_id object ---
    data["valid_id"] = {
        "type": data.pop("valid_id_type", ""),
        "number": data.pop("valid_id_number", "")
    }

    # --- Add timestamps ---
    now = datetime.now().isoformat() + "Z"
    data["created_at"] = now
    data["updated_at"] = now

    # --- Schema validation ---
    try:
        validate(instance=data, schema=reservation_schema)
    except ValidationError as e:
        print("❌ Schema Validation Error:", e.message)
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    # --- Assign unique ID ---
    data["id"] = len(reservations) + 1

    # --- Save to file ---
    reservations.append(data)
    save_reservations()

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201


# === PUT /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    data = request.get_json()
    print(f"✏️ Updating reservation #{res_id} with data:", data)

    # Find reservation
    res = next((r for r in reservations if r["id"] == res_id), None)
    if not res:
        return jsonify({"error": "Reservation not found"}), 404

    # Update editable fields
    res["guest_name"] = data.get("guest_name", res["guest_name"])
    res["resort_name"] = data.get("resort_name", res["resort_name"])
    res["guests"] = int(data.get("guests", res["guests"]))

    # Update address details
    res["address"] = f"{data.get('street_address', '')}, {data.get('municipality', '')}, {data.get('region', '')}, {data.get('country', '')}"

    # Update valid ID
    if "valid_id_type" in data or "valid_id_number" in data:
        res["valid_id"]["type"] = data.get("valid_id_type", res["valid_id"].get("type", ""))
        res["valid_id"]["number"] = data.get("valid_id_number", res["valid_id"].get("number", ""))

    # Update timestamp
    res["updated_at"] = datetime.now().isoformat() + "Z"

    # Save to file
    save_reservations()

    print("✅ Reservation updated successfully!")
    return jsonify({"message": "Reservation updated successfully!", "data": res}), 200


# === DELETE /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    global reservations
    print(f"🗑️ Deleting reservation #{res_id}")

    new_list = [r for r in reservations if r["id"] != res_id]
    if len(new_list) == len(reservations):
        return jsonify({"error": "Reservation not found"}), 404

    reservations[:] = new_list
    save_reservations()

    print("✅ Reservation deleted successfully!")
    return jsonify({"message": "Reservation deleted successfully!"}), 200


if __name__ == "__main__":
    app.run(debug=True)

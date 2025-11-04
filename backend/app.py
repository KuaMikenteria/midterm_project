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

    # Combine address fields (for readability)
    data["address"] = f"{data.get('street_address', '')}, {data.get('municipality', '')}, {data.get('region', '')}, {data.get('country', '')}"

    # Ensure contact object
    if "contact" not in data:
        data["contact"] = {
            "phone": data.pop("phone", ""),
            "email": data.pop("email", "")
        }

    # Ensure valid_id object
    if "valid_id" not in data:
        data["valid_id"] = {
            "type": data.pop("valid_id_type", ""),
            "number": data.pop("valid_id_number", "")
        }

    # Add timestamps
    now = datetime.now().isoformat() + "Z"
    data["created_at"] = now
    data["updated_at"] = now

    # Schema validation
    try:
        validate(instance=data, schema=reservation_schema)
    except ValidationError as e:
        print("❌ Schema Validation Error:", e.message)
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    # Assign unique ID
    data["id"] = len(reservations) + 1

    # Save to file
    reservations.append(data)
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201


# === PUT /reservations/<int:id> === (for edit)
@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    data = request.get_json()
    print(f"📝 Updating reservation {res_id}: {data}")

    for reservation in reservations:
        if reservation["id"] == res_id:
            # Editable fields only
            editable_fields = [
                "guest_name", "street_address", "municipality", "region",
                "country", "valid_id", "resort_name", "guests"
            ]
            for field in editable_fields:
                if field in data:
                    reservation[field] = data[field]

            # Recombine address for display
            reservation["address"] = f"{reservation.get('street_address', '')}, {reservation.get('municipality', '')}, {reservation.get('region', '')}, {reservation.get('country', '')}"

            reservation["updated_at"] = datetime.now().isoformat() + "Z"

            # Revalidate after update
            try:
                validate(instance=reservation, schema=reservation_schema)
            except ValidationError as e:
                print("❌ Validation failed during update:", e.message)
                return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

            # Save updated list
            with open(RESERVATIONS_FILE, "w") as f:
                json.dump(reservations, f, indent=2)
            print("✅ Reservation updated successfully!")
            return jsonify({"message": "Reservation updated successfully!", "data": reservation}), 200

    return jsonify({"error": "Reservation not found"}), 404


# === DELETE /reservations/<int:id> ===
@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    global reservations
    original_count = len(reservations)
    reservations = [r for r in reservations if r["id"] != res_id]

    if len(reservations) == original_count:
        return jsonify({"error": "Reservation not found"}), 404

    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print(f"🗑️ Deleted reservation {res_id}")
    return jsonify({"message": "Reservation deleted successfully!"}), 200


if __name__ == "__main__":
    app.run(debug=True)

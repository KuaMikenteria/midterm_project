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

    # Assign unique ID
    data["id"] = len(reservations) + 1

    # PERSONAL DETAILS

    # Construct contact
    data["contact"] = {
        "phone": data.pop("phone", ""),
        "email": data.pop("email", "")
    }

    # Construct valid_id
    data["valid_id"] = {
        "type": data.pop("valid_id_type", ""),
        "number": data.pop("valid_id_number", "")
    }

    #BOKING DETAILS
    # Normalize guests
    try:
        data["guests"] = int(data.get("guests", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "Guests must be an integer"}), 400

    # Default resort_id
    data["resort_id"] = data.get("resort_id", 1)

    # Add timestamps
    now = datetime.now().isoformat() + "Z"
    data["created_at"] = now
    data["updated_at"] = now

    # Validate against schema
    try:
        validate(instance=data, schema=reservation_schema)
    except ValidationError as e:
        print("❌ Schema Validation Error:", e.message)
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    # Save
    reservations.append(data)
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201


# === PUT /reservations/<id> ===
# === GET /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["GET"])
def get_reservation_by_id(res_id):
    for res in reservations:
        if res["id"] == res_id:
            return jsonify(res), 200
    return jsonify({"error": "Reservation not found"}), 404

@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    data = request.get_json()
    print(f"✏️ Updating reservation {res_id}: {data}")

    for res in reservations:
        if res["id"] == res_id:
            res.update({
                "guest_name": data.get("guest_name", res["guest_name"]),
                "street_address": data.get("street_address", res["street_address"]),
                "municipality": data.get("municipality", res["municipality"]),
                "region": data.get("region", res["region"]),
                "country": data.get("country", res["country"]),
                "valid_id": data.get("valid_id", res["valid_id"]),
                "resort_name": data.get("resort_name", res.get("resort_name")),
                "guests": int(data.get("guests", res["guests"])),
                "updated_at": datetime.now().isoformat() + "Z"
            })
            with open(RESERVATIONS_FILE, "w") as f:
                json.dump(reservations, f, indent=2)
            return jsonify({"message": "Reservation updated successfully!", "data": res}), 200

    return jsonify({"error": "Reservation not found"}), 404


# === DELETE /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    global reservations
    new_reservations = [r for r in reservations if r["id"] != res_id]

    if len(new_reservations) == len(reservations):
        return jsonify({"error": "Reservation not found"}), 404

    reservations = new_reservations
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": f"Reservation {res_id} deleted successfully!"}), 200


if __name__ == "__main__":
    app.run(debug=True)

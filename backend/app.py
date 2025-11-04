from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from jsonschema import validate, ValidationError

app = Flask(__name__)
CORS(app)

# JSON file for storage
DATA_FILE = "reservations.json"

# Load external schema file
with open("reservations.json", "r") as f:
    reservation_schema = json.load(f)

# --- Utility Functions ---
def load_data():
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# --- API Routes ---

@app.route("/reservations", methods=["GET"])
def get_reservations():
    """Fetch all reservations"""
    return jsonify(load_data())

@app.route("/reservations/<int:res_id>", methods=["GET"])
def get_reservation(res_id):
    """Get a specific reservation"""
    reservations = load_data()
    for r in reservations:
        if r["id"] == res_id:
            return jsonify(r)
    return jsonify({"error": "Reservation not found"}), 404

@app.route("/reservations", methods=["POST"])
def create_reservation():
    """Create a new reservation"""
    data = request.get_json()

    # Validate using JSON schema
    try:
        validate(instance=data, schema=reservation_schema)
    except ValidationError as e:
        return jsonify({"error": f"Invalid input: {e.message}"}), 400

    reservations = load_data()
    new_id = len(reservations) + 1
    now = datetime.utcnow().isoformat()

    new_reservation = {
        "id": new_id,
        **data,
        "created_at": now,
        "updated_at": now
    }

    reservations.append(new_reservation)
    save_data(reservations)

    return jsonify(new_reservation), 201

@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    """Update reservation details"""
    data = request.get_json()
    reservations = load_data()

    for reservation in reservations:
        if reservation["id"] == res_id:
            # Validate before update
            try:
                validate(instance=data, schema=reservation_schema)
            except ValidationError as e:
                return jsonify({"error": f"Invalid input: {e.message}"}), 400

            reservation.update(data)
            reservation["updated_at"] = datetime.utcnow().isoformat()
            save_data(reservations)
            return jsonify(reservation)

    return jsonify({"error": "Reservation not found"}), 404

@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    """Delete a reservation"""
    reservations = load_data()
    new_list = [r for r in reservations if r["id"] != res_id]

    if len(new_list) == len(reservations):
        return jsonify({"error": "Reservation not found"}), 404

    save_data(new_list)
    return jsonify({"message": f"Reservation {res_id} deleted successfully"}), 200

if __name__ == "__main__":
    app.run(debug=True)

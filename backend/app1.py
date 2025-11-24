from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import random
import string
from jsonschema import validate, ValidationError
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_FILE = "reservations.json"

##############################
#  AUTO-GENERATE SMS TOKEN   #
##############################
def generate_sms_token():
    letters_digits = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"BK-{letters_digits}"


##############################
#       JSON FILE I/O        #
##############################
def load_reservations():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_reservations(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


###########################################
#     UPDATED RESERVATION JSON SCHEMA     #
###########################################
reservation_schema = {
    "type": "object",
    "required": [
        "resort_id",
        "resort_name",
        "guest_name",
        "street_address",
        "municipality",
        "region",
        "country",
        "valid_id",
        "contact",
        "checkin_date",
        "checkout_date",
        "guests",
        "payment_gateway",
        "created_at"
    ],

    "properties": {
        "id": {"type": "integer", "minimum": 1},

        "resort_id": {"type": "integer", "minimum": 1},
        "resort_name": {"type": "string"},
        "guest_name": {"type": "string"},
        "street_address": {"type": "string"},

        "municipality": {"type": "string"},
        "region": {"type": "string"},
        "country": {"type": "string"},

        "valid_id": {
            "type": "object",
            "required": ["type", "number"],
            "properties": {
                "type": {"type": "string"},
                "number": {"type": "string", "minLength": 3}
            },
            "additionalProperties": False
        },

        "contact": {
            "type": "object",
            "required": ["phone", "email"],
            "properties": {
                "phone": {"type": "string", "pattern": "^09\\d{9}$"},
                "email": {"type": "string", "format": "email"}
            },
            "additionalProperties": False
        },

        "checkin_date": {"type": "string"},
        "checkout_date": {"type": "string"},
        "guests": {"type": "integer", "minimum": 1},

        "payment_gateway": {"type": "string"},

        "room_type": {"type": "string"},
        "notes": {"type": "string"},

        "sms_token": {
            "type": "string",
            "pattern": "^BK-[A-Z0-9]{5}$"
        },

        "created_at": {"type": "string"},
        "updated_at": {"type": "string"}
    },

    "additionalProperties": False
}



###########################################
#             API ENDPOINTS               #
###########################################


### GET ALL ###
@app.route("/reservations", methods=["GET"])
def get_reservations():
    return jsonify(load_reservations())


### POST: CREATE ###
@app.route("/reservations", methods=["POST"])
def create_reservation():
    reservation = request.get_json()

    # Auto-assign dates if frontend did not send
    reservation["created_at"] = reservation.get("created_at", datetime.utcnow().isoformat() + "Z")
    reservation["updated_at"] = reservation["created_at"]

    # Auto-generate SMS token
    reservation["sms_token"] = generate_sms_token()

    # Validate
    try:
        validate(instance=reservation, schema=reservation_schema)
    except ValidationError as e:
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    # Save
    data = load_reservations()
    reservation["id"] = len(data) + 1
    data.append(reservation)
    save_reservations(data)

    return jsonify({"message": "Reservation stored", "sms_token": reservation["sms_token"]})


### PUT: FULL UPDATE ###
@app.route("/reservations/<int:index>", methods=["PUT"])
def update_reservation(index):
    data = load_reservations()

    if index >= len(data):
        return jsonify({"error": "Index out of range"}), 404

    updated = request.get_json()

    # Preserve SMS token + ID + created_at
    updated["sms_token"] = data[index]["sms_token"]
    updated["id"] = data[index]["id"]
    updated["created_at"] = data[index]["created_at"]
    updated["updated_at"] = datetime.utcnow().isoformat() + "Z"

    # Validate
    try:
        validate(instance=updated, schema=reservation_schema)
    except ValidationError as e:
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    data[index] = updated
    save_reservations(data)

    return jsonify({"message": "Reservation updated"})


### PATCH: PARTIAL UPDATE ###
@app.route("/reservations/<int:index>", methods=["PATCH"])
def patch_reservation(index):
    data = load_reservations()

    if index >= len(data):
        return jsonify({"error": "Index out of range"}), 404

    incoming = request.get_json()

    # Apply only provided fields
    for key, value in incoming.items():
        data[index][key] = value

    # Update timestamp
    data[index]["updated_at"] = datetime.utcnow().isoformat() + "Z"

    # Re-validate full record
    try:
        validate(instance=data[index], schema=reservation_schema)
    except ValidationError as e:
        return jsonify({"error": f"Schema validation failed: {e.message}"}), 400

    save_reservations(data)
    return jsonify({"message": "Reservation patched"})


### DELETE ###
@app.route("/reservations/<int:index>", methods=["DELETE"])
def delete_reservation(index):
    data = load_reservations()

    if index >= len(data):
        return jsonify({"error": "Index out of range"}), 404

    data.pop(index)
    save_reservations(data)

    return jsonify({"message": "Reservation deleted"})


if __name__ == "__main__":
    app.run(debug=True)

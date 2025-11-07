from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import json
import os
from datetime import datetime, timezone
from jsonschema import validate, ValidationError
import re

app = Flask(__name__)

# CORS: allow everything during dev (localhost:5500 -> 127.0.0.1:5000)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False,
)

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


# ---- Helpers ----

def next_id():
    if not reservations:
        return 1
    return max(r.get("id", 0) for r in reservations) + 1


def now_utc_iso():
    # timezone-aware UTC
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


ALLOWED_VALID_IDS = {
    "PhilID/ePhilID",
    "Passport",
    "Driver's License",
    "SSS card",
    "GSIS card (UMID)",
    "PRC ID",
    "School ID",
}

PHONE_REGEX = re.compile(r"^09\d{9}$")  # strict 11-digit PH mobile (09XXXXXXXXX)


def normalize_payload(data: dict) -> dict:
    """
    Accepts BOTH styles and returns a canonical reservation dict:
      - contact: { phone, email }
      - valid_id: { type, number }
    Does NOT pop/overwrite user-provided objects accidentally.
    """
    data = dict(data or {})

    # contact
    if isinstance(data.get("contact"), dict):
        contact = {
            "phone": data["contact"].get("phone", ""),
            "email": data["contact"].get("email", ""),
        }
    else:
        contact = {
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
        }
    data["contact"] = contact

    # valid_id
    if isinstance(data.get("valid_id"), dict):
        valid_id = {
            "type": data["valid_id"].get("type", ""),
            "number": data["valid_id"].get("number", ""),
        }
    else:
        valid_id = {
            "type": data.get("valid_id_type", ""),
            "number": data.get("valid_id_number", ""),
        }
    data["valid_id"] = valid_id

    # guests -> int
    try:
        data["guests"] = int(data.get("guests", 1))
    except (ValueError, TypeError):
        data["guests"] = None  # will fail validation later with a clear message

    # default resort_id
    data["resort_id"] = data.get("resort_id", 1)

    return data


def validate_business_rules(data: dict):
    """
    Raise a readable error message (string) if something is invalid.
    """
    # Phone
    phone = data.get("contact", {}).get("phone", "")
    if not PHONE_REGEX.match(phone or ""):
        return "Phone must match 11-digit PH mobile format: 09XXXXXXXXX (e.g., 09171234567)"

    # Valid ID type
    vid_type = data.get("valid_id", {}).get("type", "")
    if vid_type not in ALLOWED_VALID_IDS:
        return (
            "valid_id.type must be one of: "
            + ", ".join(sorted(ALLOWED_VALID_IDS))
        )

    # Valid ID number
    vid_num = data.get("valid_id", {}).get("number", "")
    if not isinstance(vid_num, str) or len(vid_num) < 5:
        return "valid_id.number must be a string with at least 5 characters"

    # Guests
    guests = data.get("guests")
    if not isinstance(guests, int) or guests < 1:
        return "guests must be an integer >= 1"

    # Dates (optional extra check)
    ci = data.get("checkin_date")
    co = data.get("checkout_date")
    if ci and co and ci > co:
        return "checkout_date must be later than checkin_date"

    return None


def validate_against_schema(full_record: dict):
    """
    Validate the fully populated record against JSON schema.
    """
    try:
        validate(instance=full_record, schema=reservation_schema)
    except ValidationError as e:
        return f"Schema validation failed: {e.message}"
    return None


@app.after_request
def add_cors_headers(resp):
    # Extra CORS headers for all responses (helps with preflight/MS browsers)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp


# === OPTIONS (preflight) ===
@app.route("/reservations", methods=["OPTIONS"])
@app.route("/reservations/<int:_id>", methods=["OPTIONS"])
def options(_id=None):
    return make_response(("", 204))


# === GET /reservations ===
@app.route("/reservations", methods=["GET"])
def get_reservations():
    return jsonify(reservations), 200


# === GET /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["GET"])
def get_reservation_by_id(res_id):
    for res in reservations:
        if res.get("id") == res_id:
            return jsonify(res), 200
    return jsonify({"error": "Reservation not found"}), 404


# === POST /reservations ===
@app.route("/reservations", methods=["POST"])
def add_reservation():
    raw = request.get_json(silent=True) or {}
    print("📩 Received POST data:", raw)

    data = normalize_payload(raw)

    # Timestamps
    now = now_utc_iso()
    data["created_at"] = now
    data["updated_at"] = now

    # Merge defaults for missing optional keys to satisfy schema
    data.setdefault("resort_name", "")
    data.setdefault("street_address", "")
    data.setdefault("municipality", "")
    data.setdefault("region", "")
    data.setdefault("country", "")
    data.setdefault("payment_gateway", "")
    data.setdefault("room_type", "")
    data.setdefault("notes", "")
    data.setdefault("checkin_date", "")
    data.setdefault("checkout_date", "")

    # Business validations first (clear human-readable messages)
    err = validate_business_rules(data)
    if err:
        print("❌ Business Validation Error:", err)
        return jsonify({"error": err}), 400

    # Assign unique ID
    data["id"] = next_id()

    # Schema validation (on canonical record)
    err = validate_against_schema(data)
    if err:
        print("❌ Schema Validation Error:", err)
        return jsonify({"error": err}), 400

    # Save
    reservations.append(data)
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201


# === PUT /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    raw = request.get_json(silent=True) or {}
    print(f"✏️ Updating reservation {res_id}: {raw}")

    # find record
    idx = next((i for i, r in enumerate(reservations) if r.get("id") == res_id), None)
    if idx is None:
        return jsonify({"error": "Reservation not found"}), 404

    existing = reservations[idx]
    incoming = normalize_payload(raw)

    # Merge fields (only update those provided, keep existing otherwise)
    merged = {
        **existing,
        **{k: v for k, v in incoming.items() if v not in (None, "")},  # shallow merge
    }

    # Deep-merge contact
    merged["contact"] = {
        "phone": incoming["contact"]["phone"] or existing.get("contact", {}).get("phone", ""),
        "email": incoming["contact"]["email"] or existing.get("contact", {}).get("email", ""),
    }

    # Deep-merge valid_id
    merged["valid_id"] = {
        "type": incoming["valid_id"]["type"] or existing.get("valid_id", {}).get("type", ""),
        "number": incoming["valid_id"]["number"] or existing.get("valid_id", {}).get("number", ""),
    }

    # guests
    if incoming.get("guests") is not None:
        merged["guests"] = incoming["guests"]

    # timestamps
    merged["updated_at"] = now_utc_iso()

    # Business validations
    err = validate_business_rules(merged)
    if err:
        print("❌ Business Validation Error (PUT):", err)
        return jsonify({"error": err}), 400

    # Schema validation
    err = validate_against_schema(merged)
    if err:
        print("❌ Schema Validation Error (PUT):", err)
        return jsonify({"error": err}), 400

    # Save back
    reservations[idx] = merged
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": "Reservation updated successfully!", "data": merged}), 200


# === DELETE /reservations/<id> ===
@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    global reservations
    new_reservations = [r for r in reservations if r.get("id") != res_id]

    if len(new_reservations) == len(reservations):
        return jsonify({"error": "Reservation not found"}), 404

    reservations = new_reservations
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": f"Reservation {res_id} deleted successfully!"}), 200


if __name__ == "__main__":
    # Bind to 127.0.0.1:5000 by default
    app.run(host="127.0.0.1", port=5000, debug=True)

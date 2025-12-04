from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import json
import os
from datetime import datetime, timezone
from jsonschema import validate, ValidationError
import re
import random
import string

app = Flask(__name__)

#generate token
def generate_sms_token():
    letters = ''.join(random.choices(string.ascii_uppercase, k=1))
    digits = ''.join(random.choices(string.digits, k=5))
    return f"BK-{letters}{digits}"

# CORS
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

PHONE_REGEX = re.compile(r"^09\d{9}$")

def normalize_payload(data: dict) -> dict:
    """
    Converts incoming payload into schema-friendly canonical format.
    """
    data = dict(data or {})

    # Build contact object
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

    # Build valid_id object
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

    # guests → int
    try:
        data["guests"] = int(data.get("guests", 1))
    except (ValueError, TypeError):
        data["guests"] = None

    # default resort_id
    data["resort_id"] = data.get("resort_id", 1)

    # ✅ Remove disallowed raw fields
    for key in ("email", "phone", "valid_id_type", "valid_id_number"):
        data.pop(key, None)

    return data

def validate_business_rules(data: dict):
    phone = data.get("contact", {}).get("phone", "")
    if not PHONE_REGEX.match(phone or ""):
        return "Phone must match 11-digit PH mobile format: 09XXXXXXXXX (e.g., 09171234567)"

    vid_type = data.get("valid_id", {}).get("type", "")
    if vid_type not in ALLOWED_VALID_IDS:
        return (
            "valid_id.type must be one of: "
            + ", ".join(sorted(ALLOWED_VALID_IDS))
        )

    vid_num = data.get("valid_id", {}).get("number", "")
    if not isinstance(vid_num, str) or len(vid_num) < 5:
        return "valid_id.number must be a string with at least 5 characters"

    guests = data.get("guests")
    if not isinstance(guests, int) or guests < 1:
        return "guests must be an integer >= 1"

    ci = data.get("checkin_date")
    co = data.get("checkout_date")
    if ci and co and ci > co:
        return "checkout_date must be later than checkin_date"

    return None

def validate_against_schema(full_record: dict):
    try:
        validate(instance=full_record, schema=reservation_schema)
    except ValidationError as e:
        return f"Schema validation failed: {e.message}"
    return None

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp

@app.route("/reservations", methods=["OPTIONS"])
@app.route("/reservations/<int:_id>", methods=["OPTIONS"])
def options(_id=None):
    return make_response(("", 204))

@app.route("/reservations", methods=["GET"])
def get_reservations():
    return jsonify(reservations), 200

@app.route("/reservations/<int:res_id>", methods=["GET"])
def get_reservation_by_id(res_id):
    for res in reservations:
        if res.get("id") == res_id:
            return jsonify(res), 200
    return jsonify({"error": "Reservation not found"}), 404

@app.route("/reservations", methods=["POST"])
def add_reservation():
    raw = request.get_json(silent=True) or {}
    print("📩 Received POST data:", raw)

    data = normalize_payload(raw)

    now = now_utc_iso()
    data["created_at"] = now
    data["updated_at"] = now

    # generate SMS token only on creation
    data["sms_token"] = generate_sms_token()

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

    err = validate_business_rules(data)
    if err:
        print("❌ Business Validation Error:", err)
        return jsonify({"error": err}), 400

    data["id"] = next_id()

    err = validate_against_schema(data)
    if err:
        print("❌ Schema Validation Error:", err)
        return jsonify({"error": err}), 400

    reservations.append(data)
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    print("✅ Reservation added successfully!")
    return jsonify({"message": "Reservation added successfully!", "data": data}), 201


@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    raw = request.get_json(silent=True) or {}
    print(f"✏️ Updating reservation {res_id}: {raw}")

    idx = next((i for i, r in enumerate(reservations) if r.get("id") == res_id), None)
    if idx is None:
        return jsonify({"error": "Reservation not found"}), 404

    existing = reservations[idx]
    incoming = normalize_payload(raw)

    # === merge base fields ===
    merged = {**existing}

    for key, value in incoming.items():
        if key not in ("contact", "valid_id", "guests") and value not in ("", None):
            merged[key] = value

    merged["contact"] = {
        "phone": incoming["contact"]["phone"] or existing["contact"].get("phone", ""),
        "email": incoming["contact"]["email"] or existing["contact"].get("email", ""),
    }

    merged["valid_id"] = {
        "type": incoming["valid_id"]["type"] or existing["valid_id"].get("type", ""),
        "number": incoming["valid_id"]["number"] or existing["valid_id"].get("number", ""),
    }

    #sms token
    merged["sms_token"] = existing.get("sms_token")

    if incoming.get("guests") is not None:
        merged["guests"] = incoming["guests"]

    merged["updated_at"] = now_utc_iso()

    err = validate_business_rules(merged)
    if err:
        print("❌ Business Validation Error (PUT):", err)
        return jsonify({"error": err}), 400

    err = validate_against_schema(merged)
    if err:
        print("❌ Schema Validation Error (PUT):", err)
        return jsonify({"error": err}), 400

    reservations[idx] = merged
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": "Reservation updated successfully!", "data": merged}), 200

@app.route("/reservations/<int:res_id>", methods=["PATCH"])
def patch_reservation(res_id):
    raw = request.get_json(silent=True) or {}
    print(f"🩹 PATCH update for reservation {res_id}: {raw}")

    # Find reservation
    idx = next((i for i, r in enumerate(reservations) if r.get("id") == res_id), None)
    if idx is None:
        return jsonify({"error": "Reservation not found"}), 404

    existing = reservations[idx]
    incoming = normalize_payload(raw)

    # Start with a copy
    patched = {**existing}

    # --- Update only provided fields ---
    for key, value in incoming.items():
        # skip nested objects, handled separately
        if key not in ("contact", "valid_id", "guests") and value not in ("", None):
            patched[key] = value

    # Contact update (partial)
    patched["contact"] = {
        "phone": incoming["contact"].get("phone") or existing["contact"]["phone"],
        "email": incoming["contact"].get("email") or existing["contact"]["email"],
    }

    # Valid ID update (partial)
    patched["valid_id"] = {
        "type": incoming["valid_id"].get("type") or existing["valid_id"]["type"],
        "number": incoming["valid_id"].get("number") or existing["valid_id"]["number"],
    }

    # Guests update (partial)
    if incoming.get("guests") is not None:
        patched["guests"] = incoming["guests"]

    # sms token should not change
    patched["sms_token"] = existing.get("sms_token")

    # Set updated timestamp
    patched["updated_at"] = now_utc_iso()

    # Validate
    err = validate_business_rules(patched)
    if err:
        print("❌ Business Validation Error (PATCH):", err)
        return jsonify({"error": err}), 400

    err = validate_against_schema(patched)
    if err:
        print("❌ Schema Validation Error (PATCH):", err)
        return jsonify({"error": err}), 400

    # Save
    reservations[idx] = patched
    with open(RESERVATIONS_FILE, "w") as f:
        json.dump(reservations, f, indent=2)

    return jsonify({"message": "Partial update successful!", "data": patched}), 200

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
    app.run(host="127.0.0.1", port=5000, debug=True)

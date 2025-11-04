from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # allow frontend (localhost:5500) access

DATA_FILE = "reservations.json"


# Helper functions
def read_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def write_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# GET all reservations
@app.route("/reservations", methods=["GET"])
def get_reservations():
    data = read_data()
    return jsonify(data), 200


# POST new reservation
@app.route("/reservations", methods=["POST"])
def add_reservation():
    data = read_data()
    new_res = request.json
    new_res["id"] = data[-1]["id"] + 1 if data else 1  # auto-increment ID
    data.append(new_res)
    write_data(data)
    return jsonify({"message": "Reservation added successfully"}), 201


# PUT (update reservation by ID)
@app.route("/reservations/<int:res_id>", methods=["PUT"])
def update_reservation(res_id):
    data = read_data()
    for res in data:
        if res["id"] == res_id:
            update = request.json
            res.update(update)  # merge fields
            write_data(data)
            return jsonify({"message": "Reservation updated successfully"}), 200
    return jsonify({"error": "Reservation not found"}), 404


# DELETE reservation
@app.route("/reservations/<int:res_id>", methods=["DELETE"])
def delete_reservation(res_id):
    data = read_data()
    new_data = [r for r in data if r["id"] != res_id]
    if len(new_data) == len(data):
        return jsonify({"error": "Reservation not found"}), 404
    write_data(new_data)
    return jsonify({"message": "Reservation deleted successfully"}), 200


if __name__ == "__main__":
    app.run(debug=True)

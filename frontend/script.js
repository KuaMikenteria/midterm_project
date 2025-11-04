const API_URL = "http://127.0.0.1:5000/reservations";
const form = document.getElementById("reservationForm");
const tableBody = document.querySelector("#reservationTable tbody");
const responseMsg = document.getElementById("response");
const submitBtn = document.getElementById("submitBtn");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const editIdInput = document.getElementById("edit_id");

// date inputs
const checkinInput = document.getElementById("checkin_date");
const checkoutInput = document.getElementById("checkout_date");
const today = new Date().toISOString().split("T")[0];
checkinInput.min = today;
checkinInput.value = today;
checkinInput.addEventListener("change", () => {
  const minCo = new Date(new Date(checkinInput.value).getTime() + 86400000)
    .toISOString().split("T")[0];
  checkoutInput.min = minCo;
});

// load reservations and render
async function loadReservations() {
  try {
    const res = await fetch(API_URL);
    const data = await res.json();
    tableBody.innerHTML = "";
    data.slice().reverse().forEach(r => {
      const address = r.address || `${r.street_address || ''}, ${r.municipality || ''}, ${r.region || ''}`;
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${r.id}</td>
        <td>${r.guest_name}</td>
        <td>${address}</td>
        <td>${r.resort_name || "N/A"}</td>
        <td>${r.checkin_date}</td>
        <td>${r.checkout_date}</td>
        <td>${r.guests}</td>
        <td>${r.payment_gateway || r.payment_status || "N/A"}</td>
        <td>${r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
        <td>
          <button class="edit-btn" data-id="${r.id}">Edit</button>
          <button class="delete-btn" data-id="${r.id}">Delete</button>
        </td>
      `;
      tableBody.appendChild(row);
    });

    // attach handlers
    document.querySelectorAll(".delete-btn").forEach(b => b.addEventListener("click", onDelete));
    document.querySelectorAll(".edit-btn").forEach(b => b.addEventListener("click", onEdit));
  } catch (err) {
    console.error(err);
  }
}

// create or update handler
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearResponse();

  // build data as schema expects
  const street = document.getElementById("street_address").value || "";
  const municipal = document.getElementById("municipal").value || "";
  const region = document.getElementById("region").value || "";
  const address = `${street}, ${municipal}, ${region}`;

  const payload = {
    guest_name: document.getElementById("guest_name").value,
    street_address: street,
    municipality: municipal,
    region: region,
    address: address,
    country: document.getElementById("country").value,
    valid_id: {
      type: document.getElementById("valid_id").value,
      number: document.getElementById("valid_id_number").value
    },
    contact: {
      phone: document.getElementById("phone").value,
      email: document.getElementById("email").value
    },
    resort_name: document.getElementById("resort_name").value,
    checkin_date: document.getElementById("checkin_date").value,
    checkout_date: document.getElementById("checkout_date").value,
    guests: parseInt(document.getElementById("guests").value, 10),
    payment_gateway: document.getElementById("payment_gateway").value,
    created_at: new Date().toISOString()
  };

  // validate date logic
  if (new Date(payload.checkin_date) < new Date(today)) {
    showError("Check-in cannot be in the past.");
    return;
  }
  if (new Date(payload.checkout_date) <= new Date(payload.checkin_date)) {
    showError("Checkout date must be later than check-in.");
    return;
  }

  const editId = editIdInput.value;
  try {
    if (!editId) {
      // CREATE
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const result = await res.json();
      if (res.ok) {
        showSuccess("Reservation created.");
        form.reset();
        editIdInput.value = "";
        hideCancel();
        setDateDefaults();
        loadReservations();
      } else {
        showError(result.error || "Failed to create reservation.");
        console.error(result);
      }
    } else {
      // UPDATE: only editable fields per user spec
      const editable = {
        guest_name: payload.guest_name,
        street_address: payload.street_address,
        municipality: payload.municipality,
        region: payload.region,
        address: payload.address,
        country: payload.country,
        valid_id: payload.valid_id,
        resort_name: payload.resort_name,
        guests: payload.guests
      };
      const res = await fetch(`${API_URL}/${editId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editable)
      });
      const result = await res.json();
      if (res.ok) {
        showSuccess("Reservation updated.");
        form.reset();
        editIdInput.value = "";
        showCreateMode();
        loadReservations();
      } else {
        showError(result.error || "Failed to update reservation.");
        console.error(result);
      }
    }
  } catch (err) {
    showError("Server error.");
    console.error(err);
  }
});

// set date defaults
function setDateDefaults(){
  checkinInput.min = today;
  checkinInput.value = today;
  const minCo = new Date(new Date(today).getTime() + 86400000).toISOString().split("T")[0];
  checkoutInput.min = minCo;
  checkoutInput.value = minCo;
}

// Edit handler - prefill and switch to edit mode
async function onEdit(e) {
  const id = e.currentTarget.dataset.id;
  try {
    const res = await fetch(`${API_URL}`);
    const data = await res.json();
    const record = data.find(r => r.id === Number(id));
    if (!record) { showError("Record not found"); return; }

    // fill editable fields
    editIdInput.value = record.id;
    document.getElementById("guest_name").value = record.guest_name || "";
    // split address if it exists
    if (record.street_address) {
      document.getElementById("street_address").value = record.street_address;
      document.getElementById("municipal").value = record.municipality || "";
      document.getElementById("region").value = record.region || "";
    } else {
      // fallback: try parse address
      document.getElementById("street_address").value = record.address || "";
    }
    document.getElementById("country").value = record.country || "";
    // valid id
    if (record.valid_id) {
      document.getElementById("valid_id_type").value = record.valid_id.type || "";
      document.getElementById("valid_id_number").value = record.valid_id.number || "";
    } else {
      document.getElementById("valid_id_type").value = "";
      document.getElementById("valid_id_number").value = "";
    }
    document.getElementById("resort_name").value = record.resort_name || "";
    document.getElementById("guests").value = record.guests || 1;

    // non-editable fields - set but disable
    document.getElementById("email").value = record.contact?.email || "";
    document.getElementById("email").disabled = true;
    document.getElementById("phone").value = record.contact?.phone || "";
    document.getElementById("phone").disabled = true;
    document.getElementById("checkin_date").value = record.checkin_date || "";
    document.getElementById("checkin_date").disabled = true;
    document.getElementById("checkout_date").value = record.checkout_date || "";
    document.getElementById("checkout_date").disabled = true;
    document.getElementById("payment_gateway").value = record.payment_gateway || "";
    document.getElementById("payment_gateway").disabled = true;

    // switch UI
    submitBtn.textContent = "Save Changes";
    cancelEditBtn.style.display = "inline-block";
  } catch (err) {
    console.error(err);
    showError("Unable to fetch record for editing.");
  }
}

// Delete handler
async function onDelete(e) {
  const id = e.currentTarget.dataset.id;
  if (!confirm("Delete this reservation?")) return;
  try {
    const res = await fetch(`${API_URL}/${id}`, { method: "DELETE" });
    if (res.ok) {
      showSuccess("Reservation deleted.");
      loadReservations();
    } else {
      const err = await res.json();
      showError(err.error || "Delete failed");
    }
  } catch (err) {
    console.error(err);
    showError("Server error.");
  }
}

// Cancel edit
document.getElementById("cancelEditBtn").addEventListener("click", () => {
  form.reset();
  editIdInput.value = "";
  showCreateMode();
  setDateDefaults();
});

// helpers
function showError(msg) {
  responseMsg.textContent = msg;
  responseMsg.className = "error";
}
function showSuccess(msg) {
  responseMsg.textContent = msg;
  responseMsg.className = "success";
}
function clearResponse() {
  responseMsg.textContent = "";
  responseMsg.className = "";
}
function showCreateMode() {
  submitBtn.textContent = "Create Reservation";
  cancelEditBtn.style.display = "none";
  // enable non-editable fields for create
  document.getElementById("email").disabled = false;
  document.getElementById("phone").disabled = false;
  document.getElementById("checkin_date").disabled = false;
  document.getElementById("checkout_date").disabled = false;
  document.getElementById("payment_gateway").disabled = false;
}

// initial
setDateDefaults();
loadReservations();

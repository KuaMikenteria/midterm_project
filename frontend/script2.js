const API_URL = "http://127.0.0.1:5000/reservations";

const form = document.getElementById("reservationForm");
const tableBody = document.querySelector("#reservationsTable tbody");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const submitBtn = document.getElementById("submitBtn");

let editMode = false;
let editId = null;

// Date restrictions (checkin cannot be in the past)
const checkinInput = document.getElementById("checkin_date");
const checkoutInput = document.getElementById("checkout_date");
const today = new Date().toISOString().split("T")[0];
if (checkinInput) checkinInput.min = today;
checkinInput?.addEventListener("change", () => {
  const d = new Date(checkinInput.value);
  d.setDate(d.getDate() + 1);
  checkoutInput.min = d.toISOString().split("T")[0];
});

// Phone validation (strict 09XXXXXXXXX)
const phoneInput = document.getElementById("phone");
if (phoneInput) {
  phoneInput.addEventListener("input", () => {
    const pattern = /^09\d{9}$/;
    if (!pattern.test(phoneInput.value)) {
      phoneInput.setCustomValidity("Please enter a valid PH mobile number (11 digits, e.g., 09171234567)");
    } else {
      phoneInput.setCustomValidity("");
    }
  });
}

function escapeHtml(str) {
  if (!str && str !== 0) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function fetchReservations() {
  try {
    const res = await fetch(API_URL);
    const data = await res.json();
    tableBody.innerHTML = "";
    data.slice().reverse().forEach(record => {
      const addr = [record.street_address, record.municipality, record.region, record.country].filter(Boolean).join(", ");
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${record.id}</td>
        <td>${escapeHtml(record.guest_name)}</td>
        <td>${escapeHtml(addr)}</td>
        <td>${escapeHtml(record.resort_name || "")}</td>
        <td>${record.checkin_date || ""}</td>
        <td>${record.checkout_date || ""}</td>
        <td>${record.guests}</td>
        <td>${escapeHtml(record.payment_gateway || "")}</td>
        <td>
          <button class="action-btn view-btn" data-id="${record.id}">View</button>
          <button class="action-btn edit-btn" data-id="${record.id}">Edit</button>
          <button class="action-btn delete-btn" data-id="${record.id}">Delete</button>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading reservations:", err);
    tableBody.innerHTML = `<tr><td colspan="9">Failed to load reservations.</td></tr>`;
  }
}

async function viewReservation(id) {
  try {
    const res = await fetch(`${API_URL}/${id}`);
    if (!res.ok) { alert("Failed to fetch reservation details."); return; }
    const r = await res.json();
    const details = {
      ID: r.id,
      Guest: r.guest_name,
      Email: r.contact?.email || "-",
      Phone: r.contact?.phone || "-",
      Address: [r.street_address, r.municipality, r.region, r.country].filter(Boolean).join(", "),
      Resort: r.resort_name || "-",
      "Check-in": r.checkin_date || "-",
      "Check-out": r.checkout_date || "-",
      Guests: r.guests,
      Payment: r.payment_gateway || "-",
      "Valid ID": `${r.valid_id?.type || "-"} (${r.valid_id?.number || "-"})`,
      "Created At": r.created_at || "-",
      "SMS Token": r.sms_token || "(not available)"
    };
    const pretty = Object.entries(details).map(([k,v])=> `${k}: ${v}`).join("\n");
    // show in modal
    const modal = document.getElementById("viewModal");
    const modalDetails = document.getElementById("modalDetails");
    modalDetails.textContent = pretty;
    modal.style.display = "block";
    modal.setAttribute("aria-hidden", "false");
  } catch (err) {
    console.error("viewReservation error:", err);
    alert("Error fetching reservation.");
  }
}

async function editReservation(id) {
  try {
    const res = await fetch(`${API_URL}/${id}`);
    if (!res.ok) { alert("Reservation not found"); return; }
    const rec = await res.json();

    // populate form (fields that exist)
    form.guest_name.value = rec.guest_name || "";
    form.street_address.value = rec.street_address || "";
    form.municipality.value = rec.municipality || "";
    form.region.value = rec.region || "";
    form.country.value = rec.country || "";
    form.valid_id_type.value = rec.valid_id?.type || "";
    form.valid_id_number.value = rec.valid_id?.number || "";
    form.email.value = rec.contact?.email || "";
    form.phone.value = rec.contact?.phone || "";
    form.resort_name.value = rec.resort_name || "";
    form.checkin_date.value = rec.checkin_date || "";
    form.checkout_date.value = rec.checkout_date || "";
    form.guests.value = rec.guests || 1;
    form.payment_gateway.value = rec.payment_gateway || "";

    editMode = true;
    editId = id;
    submitBtn.textContent = "Update Reservation";
    cancelEditBtn.style.display = "inline-block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    console.error("editReservation error:", err);
    alert("Failed to load reservation for edit.");
  }
}

async function deleteReservation(id) {
  if (!confirm("Delete this reservation?")) return;
  try {
    const res = await fetch(`${API_URL}/${id}`, { method: "DELETE" });
    if (res.ok) {
      await fetchReservations();
    } else {
      const info = await res.json().catch(()=>({}));
      alert("Delete failed: " + (info.error || res.status));
    }
  } catch (err) {
    console.error("deleteReservation error:", err);
    alert("Delete failed due to network error.");
  }
}

tableBody.addEventListener("click", (e) => {
  const btn = e.target;
  const id = btn.dataset.id;
  if (!id) return;
  if (btn.classList.contains("view-btn")) viewReservation(id);
  else if (btn.classList.contains("edit-btn")) editReservation(id);
  else if (btn.classList.contains("delete-btn")) deleteReservation(id);
});

// modal close
document.getElementById("closeModal").addEventListener("click", () => {
  const modal = document.getElementById("viewModal");
  modal.style.display = "none";
  modal.setAttribute("aria-hidden", "true");
});

// submit handler - both create and update
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  // phone check
  const phoneVal = form.phone.value.trim();
  if (!/^09\d{9}$/.test(phoneVal)) {
    alert("Phone format invalid. Use 11-digit PH mobile (e.g., 09171234567)");
    return;
  }

  // check dates
  if (form.checkin_date.value && form.checkout_date.value) {
    if (new Date(form.checkout_date.value) <= new Date(form.checkin_date.value)) {
      alert("Checkout date must be later than check-in date.");
      return;
    }
  }

  // payload with frontend fields; backend normalizes
  const payload = {
    resort_name: form.resort_name.value,
    guest_name: form.guest_name.value,
    street_address: form.street_address.value,
    municipality: form.municipality.value,
    region: form.region.value,
    country: form.country.value,
    valid_id_type: form.valid_id_type.value,
    valid_id_number: form.valid_id_number.value,
    email: form.email.value,
    phone: form.phone.value,
    checkin_date: form.checkin_date.value,
    checkout_date: form.checkout_date.value,
    guests: parseInt(form.guests.value, 10) || 1,
    payment_gateway: form.payment_gateway.value
  };

  try {
    const url = editMode ? `${API_URL}/${editId}` : API_URL;
    const method = editMode ? "PUT" : "POST";
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json().catch(()=>({}));
      alert(editMode ? "Reservation updated!" : "Reservation created!");
      form.reset();
      editMode = false;
      editId = null;
      submitBtn.textContent = "Create Reservation";
      cancelEditBtn.style.display = "none";
      await fetchReservations();
      console.log("Server response:", data);
    } else {
      const info = await res.json().catch(()=>({}));
      console.error("Server validation error:", info);
      alert("Error: " + (info.error || "Validation failed"));
    }
  } catch (err) {
    console.error("submit error:", err);
    alert("Network or server error when submitting.");
  }
});

cancelEditBtn.addEventListener("click", () => {
  form.reset();
  editMode = false;
  editId = null;
  submitBtn.textContent = "Create Reservation";
  cancelEditBtn.style.display = "none";
});

fetchReservations();

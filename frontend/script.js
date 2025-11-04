const form = document.getElementById("reservationForm");
const tableBody = document.querySelector("#reservationTable tbody");
const responseMsg = document.getElementById("response");

const API_URL = "http://127.0.0.1:5000/reservations"; // adjust if different

// Load existing reservations
async function loadReservations() {
  tableBody.innerHTML = "";
  const res = await fetch(API_URL);
  const data = await res.json();

  data.forEach((reservation) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${reservation.id}</td>
      <td>${reservation.guest_name}</td>
      <td>${reservation.resort_name}</td>
      <td>${reservation.checkin_date}</td>
      <td>${reservation.checkout_date}</td>
      <td>${reservation.guests}</td>
      <td>${reservation.payment_status}</td>
      <td>
        <button onclick="editReservation(${reservation.id})">Edit</button>
        <button onclick="deleteReservation(${reservation.id})">Delete</button>
      </td>
    `;
    tableBody.appendChild(row);
  });
}

// Submit new reservation
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const newReservation = {
    guest_name: form.guest_name.value,
    address: form.address.value,
    country: form.country.value,
    legal_id: form.legal_id.value,
    email: form.email.value,
    phone: form.phone.value,
    resort_name: form.resort_name.value,
    checkin_date: form.checkin_date.value,
    checkout_date: form.checkout_date.value,
    guests: form.guests.value,
    payment_status: form.payment_status.value
  };

  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(newReservation)
  });

  if (res.ok) {
    responseMsg.textContent = "✅ Reservation added successfully!";
    form.reset();
    loadReservations();
  } else {
    responseMsg.textContent = "❌ Failed to add reservation!";
  }
});

// Edit reservation
async function editReservation(id) {
  const newStatus = prompt("Enter new payment status (pending, paid, failed, refunded):");
  if (!newStatus) return;

  await fetch(`${API_URL}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payment_status: newStatus })
  });

  loadReservations();
}

// Delete reservation
async function deleteReservation(id) {
  if (confirm("Are you sure you want to delete this reservation?")) {
    await fetch(`${API_URL}/${id}`, { method: "DELETE" });
    loadReservations();
  }
}

// Initialize
loadReservations();

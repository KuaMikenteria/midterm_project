const API_URL = "http://127.0.0.1:5000/reservations";
const form = document.getElementById("reservationForm");
const tableBody = document.querySelector("#reservationTable tbody");
const responseMsg = document.getElementById("response");

// --- Date Restrictions ---
const checkinInput = document.getElementById("checkin_date");
const checkoutInput = document.getElementById("checkout_date");

// Only allow current/future date for check-in
const today = new Date().toISOString().split("T")[0];
checkinInput.min = today;

// When check-in changes, checkout must be at least 1 day after
checkinInput.addEventListener("change", () => {
  const checkin = new Date(checkinInput.value);
  checkin.setDate(checkin.getDate() + 1);
  checkoutInput.min = checkin.toISOString().split("T")[0];
});

// --- Fetch Reservations ---
async function loadReservations() {
  const res = await fetch(API_URL);
  const data = await res.json();
  tableBody.innerHTML = "";
  data.forEach(r => {
    const row = `
      <tr>
        <td>${r.id}</td>
        <td>${r.guest_name}</td>
        <td>${r.resort_name || "N/A"}</td>
        <td>${r.checkin_date}</td>
        <td>${r.checkout_date}</td>
        <td>${r.guests}</td>
        <td>${r.payment_status}</td>
        <td>${r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
      </tr>
    `;
    tableBody.insertAdjacentHTML("beforeend", row);
  });
}

// --- Submit Reservation ---
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const data = {
    guest_name: document.getElementById("guest_name").value,
    address: document.getElementById("address").value,
    country: document.getElementById("country").value,
    legal_id: document.getElementById("legal_id").value,
    email: document.getElementById("email").value,
    phone: document.getElementById("phone").value,
    resort_name: document.getElementById("resort_name").value,
    checkin_date: document.getElementById("checkin_date").value,
    checkout_date: document.getElementById("checkout_date").value,
    guests: document.getElementById("guests").value,
    payment_status: document.getElementById("payment_status").value
  };

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });

    const result = await res.json();

    if (res.ok) {
      responseMsg.textContent = "✅ Reservation submitted successfully!";
      loadReservations();
      form.reset();
    } else {
      responseMsg.textContent = "❌ Failed: " + (result.error || "Unknown error");
      console.error(result);
    }
  } catch (err) {
    responseMsg.textContent = "⚠️ Error connecting to server.";
    console.error(err);
  }
});

// Initial load
loadReservations();

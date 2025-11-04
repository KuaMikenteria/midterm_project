const API_URL = "http://127.0.0.1:5000/reservations";
const form = document.getElementById("reservationForm");
const tableBody = document.querySelector("#reservationTable tbody");
const responseMsg = document.getElementById("response");

// --- Date Restrictions ---
const checkinInput = document.getElementById("checkin_date");
const checkoutInput = document.getElementById("checkout_date");

// Restrict check-in to today or future
const today = new Date().toISOString().split("T")[0];
checkinInput.min = today;

// Checkout must always be at least 1 day after check-in
checkinInput.addEventListener("change", () => {
  const checkin = new Date(checkinInput.value);
  checkin.setDate(checkin.getDate() + 1);
  checkoutInput.min = checkin.toISOString().split("T")[0];
});

// --- Load Reservations Table ---
async function loadReservations() {
  try {
    const res = await fetch(API_URL);
    const data = await res.json();
    tableBody.innerHTML = "";
    data.forEach(r => {
      const row = `
        <tr>
          <td>${r.id}</td>
          <td>${r.guest_name}</td>
          <td>${r.street_address}, ${r.municipality}, ${r.region}</td>
          <td>${r.country}</td>
          <td>${r.contact?.phone || "N/A"}</td>
          <td>${r.checkin_date}</td>
          <td>${r.checkout_date}</td>
          <td>${r.guests}</td>
          <td>${r.payment_gateway}</td>
          <td>${r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
        </tr>
      `;
      tableBody.insertAdjacentHTML("beforeend", row);
    });
  } catch (err) {
    console.error("Error loading reservations:", err);
  }
}

// --- Submit Reservation ---
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const phone = document.getElementById("phone").value.trim();
  const phonePattern = /^(\+63|0)9\d{9}$/;
  if (!phonePattern.test(phone)) {
    responseMsg.textContent = "❌ Invalid phone number format. Use +639XXXXXXXXX or 09XXXXXXXXX.";
    return;
  }

  const data = {
    resort_id: 1, // example static ID, adjust as needed
    guest_name: document.getElementById("guest_name").value,
    street_address: document.getElementById("street_address").value,
    municipality: document.getElementById("municipality").value,
    region: document.getElementById("region").value,
    country: document.getElementById("country").value,
    valid_id: {
      type: document.getElementById("valid_id_type").value,
      number: document.getElementById("valid_id_number").value
    },
    contact: {
      phone: phone,
      email: document.getElementById("email").value
    },
    checkin_date: document.getElementById("checkin_date").value,
    checkout_date: document.getElementById("checkout_date").value,
    guests: parseInt(document.getElementById("guests").value),
    payment_gateway: document.getElementById("payment_gateway").value,
    created_at: new Date().toISOString()
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
      form.reset();
      loadReservations();
    } else {
      responseMsg.textContent = "❌ Failed: " + (result.error || "Unknown error");
      console.error("Validation Error:", result);
    }
  } catch (err) {
    responseMsg.textContent = "⚠️ Error connecting to server.";
    console.error("Network Error:", err);
  }
});

// Initial load
loadReservations();

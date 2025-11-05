const API_URL = "http://127.0.0.1:5000/reservations";
const form = document.getElementById("reservationForm");
const tableBody = document.querySelector("#reservationTable tbody");
const responseMsg = document.getElementById("response");
const searchBox = document.getElementById("searchBox");
let allReservations = [];

async function loadReservations() {
  const res = await fetch(API_URL);
  allReservations = await res.json();
  renderTable(allReservations);
}

function renderTable(data) {
  tableBody.innerHTML = "";

  data.slice().reverse().forEach(r => {
    const row = document.createElement("tr");
    const fullAddress = `${r.street_address}, ${r.municipality}, ${r.region}, ${r.country}`;
    row.innerHTML = `
      <td>${r.id}</td>
      <td>${r.guest_name}</td>
      <td>${fullAddress}</td>
      <td>${r.resort_name}</td>
      <td>${r.checkin_date}</td>
      <td>${r.checkout_date}</td>
      <td>${r.guests}</td>
      <td>${r.payment_gateway}</td>
      <td>${new Date(r.created_at).toLocaleString()}</td>
      <td>
        <button class="view-btn" data-id="${r.id}">View Details</button>
        <button class="edit-btn" data-id="${r.id}">Edit</button>
        <button class="delete-btn" data-id="${r.id}">Delete</button>
      </td>
    `;
    tableBody.appendChild(row);

    const detailsRow = document.createElement("tr");
    detailsRow.classList.add("details-row");
    detailsRow.style.display = "none";
    detailsRow.innerHTML = `
      <td colspan="10" class="details-cell">
        <div class="details-box">
          <strong>Email:</strong> ${r.contact?.email || ""}<br>
          <strong>Phone:</strong> ${r.contact?.phone || ""}<br>
          <strong>Valid ID:</strong> ${r.valid_id?.type || ""} - ${r.valid_id?.number || ""}<br>
          <strong>Updated:</strong> ${r.updated_at ? new Date(r.updated_at).toLocaleString() : "-"}
        </div>
      </td>
    `;
    tableBody.appendChild(detailsRow);
  });

  document.querySelectorAll(".view-btn").forEach(btn => btn.addEventListener("click", toggleDetails));
}

searchBox.addEventListener("input", e => {
  const query = e.target.value.toLowerCase();
  const filtered = allReservations.filter(r =>
    r.guest_name.toLowerCase().includes(query) ||
    r.resort_name.toLowerCase().includes(query) ||
    r.municipality.toLowerCase().includes(query)
  );
  renderTable(filtered);
});

function toggleDetails(e) {
  const row = e.target.closest("tr");
  const next = row.nextElementSibling;
  if (next && next.classList.contains("details-row")) {
    next.style.display = next.style.display === "none" ? "table-row" : "none";
    e.target.textContent = next.style.display === "none" ? "View Details" : "Hide Details";
  }
}

loadReservations();

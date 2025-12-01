const API_URL = "http://localhost:5000/bookings";  

let updateID = null;

// Load data on page load
document.addEventListener("DOMContentLoaded", loadBookings);

function loadBookings() {
  fetch(API_URL)
    .then(res => res.json())
    .then(data => {
      const tbody = document.querySelector("#booking-table tbody");
      tbody.innerHTML = "";

      data.forEach(item => {
        const row = `
          <tr>
            <td>${item.id}</td>
            <td>${item.name}</td>
            <td>${item.email}</td>
            <td>${item.date}</td>
            <td>${item.sms_token}</td>  <!-- visible only here -->
            <td>
              <button onclick="editBooking(${item.id})">Edit</button>
              <button onclick="deleteBooking(${item.id})">Delete</button>
            </td>
          </tr>
        `;
        tbody.innerHTML += row;
      });
    });
}


// Add or Update form submit
function submitForm() {
  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const date = document.getElementById("date").value;

  if (!name || !email || !date) {
    alert("All fields except SMS Token are required!");
    return;
  }

  const data = { name, email, date };

  if (updateID === null) {
    // CREATE (POST)
    fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(res => res.json())
      .then(() => {
        alert("Booking Added!");
        loadBookings();
        resetForm();
      });

  } else {
    // UPDATE (PATCH)
    fetch(`${API_URL}/${updateID}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(res => res.json())
      .then(() => {
        alert("Booking Updated!");
        loadBookings();
        resetForm();
      });
  }
}


// Load data into form for editing
function editBooking(id) {
  fetch(`${API_URL}/${id}`)
    .then(res => res.json())
    .then(item => {
      updateID = id;
      document.getElementById("form-title").innerText = "Edit Booking";

      document.getElementById("name").value = item.name;
      document.getElementById("email").value = item.email;
      document.getElementById("date").value = item.date;

      // SMS token stays HIDDEN and NOT editable
    });
}


// Delete booking
function deleteBooking(id) {
  if (!confirm("Delete this booking?")) return;

  fetch(`${API_URL}/${id}`, {
    method: "DELETE"
  }).then(() => {
    alert("Booking Removed!");
    loadBookings();
  });
}


// Reset form to create mode
function resetForm() {
  updateID = null;
  document.getElementById("form-title").innerText = "Add Booking";
  document.getElementById("name").value = "";
  document.getElementById("email").value = "";
  document.getElementById("date").value = "";
}

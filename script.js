// Your Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAERi_sy9t-jC8WdpFZdmyj4gmHNv9_Hng",
  authDomain: "capstone-b1d2a.firebaseapp.com",
  databaseURL: "https://capstone-b1d2a-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "capstone-b1d2a",
  storageBucket: "capstone-b1d2a.firebasestorage.app",
  messagingSenderId: "771505862312",
  appId: "1:771505862312:web:78d64417b8ae5253a7b49d",
  measurementId: "G-74TWMV04TH"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Get a reference to the database service
const db = firebase.database();

// Test Firebase connection
db.ref('.info/connected').on('value', (snapshot) => {
  if (snapshot.val() === true) {
    console.log("Firebase connected successfully!");
  } else {
    console.error("Firebase connection failed.");
  }
});

// Reference to telemetry
const telemetryRef = db.ref('ugv/telemetry');

// Real-time listener
telemetryRef.on('value', (snapshot) => {
  const data = snapshot.val();
  console.log("Data received from Firebase:", data); // Log the data from Firebase
  if (data) {
    updateDashboard(data);
  }
});

function updateDashboard(data) {
  // Add null checks for data properties
  const safeData = {
    speed: data.speed || 0,
    battery: data.battery || 0,
    gps: data.gps || { accuracy: 0 },
    current_task: data.current_task || 'No active task',
    heading: data.heading || 0
  };

  // Update speed display
  document.getElementById('speed').textContent = 
    `${safeData.speed.toLocaleString('en-US', { maximumFractionDigits: 1 })} km/h`;

  // Update battery display
  document.getElementById('battery').textContent = 
    `${Math.round(safeData.battery)}%`;

  // Update GPS accuracy
  document.getElementById('gps').textContent = 
    `${safeData.gps.accuracy.toFixed(1).replace('.', ',')} m`;

  // Update current task
  document.getElementById('task').textContent = safeData.current_task;

  // Update map position if lat/lon present
  if (data.gps && data.gps.lat && data.gps.lon) {
    updateMapPosition(data.gps.lat, data.gps.lon, data.heading);
  }
}

// Optionally, add DOMContentLoaded event for initialization messages
window.addEventListener('DOMContentLoaded', () => {
  console.log("Dashboard initialized and waiting for Firebase data...");
});

let map, marker;

function initMap(lat = -36.8485, lon = 174.7633) {
  // Only initialize once
  if (map) return;
  map = L.map('map').setView([lat, lon], 16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  marker = L.marker([lat, lon]).addTo(map);
}

// Call this when new telemetry data arrives
function updateMapPosition(lat, lon, heading) {
  if (!map) initMap(lat, lon);
  marker.setLatLng([lat, lon]);
  map.setView([lat, lon]);
  // Optionally, rotate marker for heading (needs a plugin)
}

async function fetchTelemetry() {
  try {
    const response = await fetch('http://96.0.77.42:5000/api/telemetry');
    const data = await response.json();

    if (!data || data.length === 0) {
      console.warn("No telemetry data received");
      return;
    }

    // Find latest by timestamp
    const latest = data.reduce((a, b) => (a.timestamp > b.timestamp ? a : b));

    // Update dashboard
    updateDashboard(latest);
  } catch (error) {
    console.error("Error fetching telemetry:", error);
  }
}

function updateDashboard(data) {
  document.getElementById('speed').textContent = `${parseFloat(data.speed || 0).toFixed(2)} km/h`;
  document.getElementById('battery').textContent = `${data.battery_remaining || 'N/A'}%`;
  document.getElementById('gps').textContent = `N/A`;
  document.getElementById('task').textContent = `Idle`;

  if (data.lat && data.lon && data.lat !== "0" && data.lon !== "0") {
    updateMapPosition(parseFloat(data.lat), parseFloat(data.lon), parseFloat(data.heading || 0));
  }
}

let map, marker;

function initMap(lat = -36.8485, lon = 174.7633) {
  if (map) return;
  map = L.map('map').setView([lat, lon], 16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
  marker = L.marker([lat, lon]).addTo(map);
}

function updateMapPosition(lat, lon, heading) {
  if (!map) initMap(lat, lon);
  marker.setLatLng([lat, lon]);
  map.setView([lat, lon]);
}

fetchTelemetry();
setInterval(fetchTelemetry, 2000);


async function startRealSenseStream() {
  const video = document.getElementById('realsenseStream');
  const pc = new RTCPeerConnection();

  pc.ontrack = (event) => {
    video.srcObject = event.streams[0];
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const response = await fetch('http://10.244.51.157:8080/offer', {
    method: 'POST',
    body: JSON.stringify(pc.localDescription),
    headers: { 'Content-Type': 'application/json' }
  });
  const answer = await response.json();
  await pc.setRemoteDescription(answer);
}

startRealSenseStream();

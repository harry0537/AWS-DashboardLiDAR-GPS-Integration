async function fetchTelemetry() {
    try {
    const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/telemetry/latest`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    if (!data || Object.keys(data).length === 0) {
      console.warn("No telemetry data received");
      return;
    }

    // Update dashboard
    updateDashboard(data);
  } catch (error) {
    console.error("Error fetching telemetry:", error);
  }
}

async function fetchLiDARData() {
    try {
        const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/lidar/latest`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data && data.object_avoidance) {
            updateLiDARDisplay(data.object_avoidance);
        }
    } catch (error) {
        console.error("Error fetching LiDAR data:", error);
    }
}

async function fetchUltrasonicData() {
    try {
        const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/ultrasonic/latest`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data && data.distance_cm) {
            updateUltrasonicDisplay(data);
        }
    } catch (error) {
        console.error("Error fetching ultrasonic data:", error);
    }
}

async function fetchBatteryData() {
    try {
        const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/battery/latest`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        if (data && data.voltage) {
            updateBatteryDisplay(data);
        }
    } catch ( error) {
        console.error("Error fetching battery data:", error);
    }
}

function updateDashboard(data) {
  document.getElementById('speed').textContent = `${parseFloat(data.speed || 0).toFixed(2)} km/h`;
  document.getElementById('battery').textContent = `${data.battery_remaining || 'N/A'}%`;
  const hdop = data.gps_accuracy_hdop;
  document.getElementById('gps').textContent = (hdop !== undefined && hdop !== null) ? `${hdop} HDOP` : 'N/A';
  document.getElementById('task').textContent = `Idle`;

  if (data.lat && data.lon && data.lat !== "0" && data.lon !== "0") {
    updateMapPosition(parseFloat(data.lat), parseFloat(data.lon), parseFloat(data.heading || 0));
  }
}

function updateLiDARDisplay(lidarData) {
    // Update LiDAR information in dashboard
    const lidarInfo = document.getElementById('lidar-info');
    if (lidarInfo) {
        lidarInfo.innerHTML = `
            <div class="sensor-data">
                <h4>LiDAR Object Detection</h4>
                <p>Closest Object: <strong>${lidarData.closest_distance_cm} cm</strong></p>
                <p>Distance: <strong>${lidarData.closest_distance_m} m</strong></p>
                <p>Measurements: <strong>${lidarData.measurement_count}</strong></p>
            </div>
        `;
    }
}

function updateUltrasonicDisplay(data) {
    // Update ultrasonic information in dashboard
    const ultrasonicInfo = document.getElementById('ultrasonic-info');
    if (ultrasonicInfo) {
        const statusClass = data.status === 'normal' ? 'status-normal' : 'status-warning';
        ultrasonicInfo.innerHTML = `
            <div class="sensor-data ${statusClass}">
                <h4>Ultrasonic Sensor (Maxbotix I2C EZ4)</h4>
                <p>Distance: <strong>${data.distance_cm} cm</strong></p>
                <p>Range: <strong>${data.distance_m} m</strong></p>
                <p>Status: <strong>${data.status}</strong></p>
            </div>
        `;
    }
}

function updateBatteryDisplay(data) {
    // Update battery information in dashboard
    const batteryElement = document.getElementById('battery');
    if (batteryElement) {
        const voltage = data.voltage;
        const threshold = data.voltage_threshold;
        const status = data.status;
        
        // Color code based on battery status
        if (status === 'low_battery') {
            batteryElement.className = 'battery-low';
            batteryElement.textContent = `${voltage}V (LOW!)`;
        } else {
            batteryElement.className = 'battery-normal';
            batteryElement.textContent = `${voltage}V`;
        }
        
        // Show RTL warning if triggered
        if (data.rtl_triggered) {
            showRTLWarning(data.rtl_reason);
        }
    }
}

function showRTLWarning(reason) {
    // Display RTL warning notification
    const warningDiv = document.createElement('div');
    warningDiv.className = 'rtl-warning';
    warningDiv.innerHTML = `
        <div class="warning-content">
            <span class="warning-icon">🚨</span>
            <span class="warning-text">RTL TRIGGERED: ${reason}</span>
            <button onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add to page if not already present
    if (!document.querySelector('.rtl-warning')) {
        document.body.appendChild(warningDiv);
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

// Initialize dashboard with all sensor data
function initializeDashboard() {
    fetchTelemetry();
    fetchLiDARData();
    fetchUltrasonicData();
    fetchBatteryData();
}

// Set up periodic updates
initializeDashboard();
setInterval(fetchTelemetry, 2000);
setInterval(fetchLiDARData, 1000);      // LiDAR updates faster for object avoidance
setInterval(fetchUltrasonicData, 500);  // Ultrasonic updates at 2Hz
setInterval(fetchBatteryData, 5000);   // Battery check every 5 seconds

async function startRealSenseStream() {
  const video = document.getElementById('realsenseStream');
  const pc = new RTCPeerConnection();

  pc.ontrack = (event) => {
    video.srcObject = event.streams[0];
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const response = await fetch(window.APP_CONFIG.WEBRTC_OFFER_URL, {
    method: 'POST',
    body: JSON.stringify(pc.localDescription),
    headers: { 'Content-Type': 'application/json' }
  });
  const answer = await response.json();
  await pc.setRemoteDescription(answer);
}

startRealSenseStream();

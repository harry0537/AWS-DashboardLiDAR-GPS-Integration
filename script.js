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
    // Update LiDAR information in dashboard with enhanced obstacle detection
    const lidarInfo = document.getElementById('lidar-info');
    if (lidarInfo && lidarData.object_avoidance) {
        const data = lidarData.object_avoidance;
        const status = data.status || 'unknown';
        const statusClass = getStatusClass(status);
        
        // Create sector display
        let sectorsHtml = '';
        if (data.sectors) {
            sectorsHtml = '<div class="sectors-grid">';
            for (const [sectorName, sectorData] of Object.entries(data.sectors)) {
                const dangerClass = getDangerClass(sectorData.danger_level);
                sectorsHtml += `
                    <div class="sector ${dangerClass}">
                        <h5>${sectorName.toUpperCase()}</h5>
                        <p>Distance: <strong>${sectorData.closest_cm} cm</strong></p>
                        <p>Status: <strong>${sectorData.danger_level}</strong></p>
                    </div>
                `;
            }
            sectorsHtml += '</div>';
        }
        
        lidarInfo.innerHTML = `
            <div class="sensor-data ${statusClass}">
                <h4>🛡️ LiDAR Obstacle Detection</h4>
                <div class="lidar-status">
                    <p>Status: <strong>${status.toUpperCase()}</strong></p>
                    <p>Closest Object: <strong>${data.closest_distance_cm} cm</strong></p>
                    <p>Distance: <strong>${data.closest_distance_m} m</strong></p>
                    <p>Measurements: <strong>${data.measurement_count}</strong></p>
                    <p>Quality: <strong>${data.quality_avg || 'N/A'}</strong></p>
                </div>
                ${sectorsHtml}
            </div>
        `;
        
        // Update status indicator
        updateObstacleStatus(status, data.closest_distance_cm);
    }
}

function getStatusClass(status) {
    switch (status) {
        case 'critical': return 'status-critical';
        case 'warning': return 'status-warning';
        case 'caution': return 'status-caution';
        case 'clear': return 'status-normal';
        default: return 'status-unknown';
    }
}

function getDangerClass(dangerLevel) {
    switch (dangerLevel) {
        case 'high': return 'danger-high';
        case 'medium': return 'danger-medium';
        case 'low': return 'danger-low';
        case 'none': return 'danger-none';
        default: return 'danger-none';
    }
}

function updateObstacleStatus(status, distance) {
    // Update obstacle status indicator
    const statusIndicator = document.getElementById('obstacle-status');
    if (statusIndicator) {
        const statusClass = getStatusClass(status);
        statusIndicator.className = `obstacle-indicator ${statusClass}`;
        statusIndicator.textContent = `${status.toUpperCase()} (${distance}cm)`;
    }
    
    // Show alert for critical situations
    if (status === 'critical') {
        showObstacleAlert(distance);
    }
}

function showObstacleAlert(distance) {
    // Display critical obstacle alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'obstacle-alert';
    alertDiv.innerHTML = `
        <div class="alert-content">
            <span class="alert-icon">🚨</span>
            <span class="alert-text">CRITICAL OBSTACLE: ${distance}cm</span>
            <button onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add to page if not already present
    if (!document.querySelector('.obstacle-alert')) {
        document.body.appendChild(alertDiv);
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

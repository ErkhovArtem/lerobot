import asyncio
import json
import socket
import ssl
import os
import cv2
import numpy as np
import threading
from aiohttp import web

class PhoneServer:
    """Main server class for iPhone IMU and RealSense camera streaming"""
    
    HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="screen-orientation" content="landscape">
    <title>XLeRobotHead - VR Mode</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            display: flex;
            flex-direction: row;
            align-items: stretch;
        }
        /* VR Display Container */
        .vr-container {
            display: flex;
            width: 100vw;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
        }
        .eye-container {
            width: 50%;
            height: 100vh;
            overflow: hidden;
            background: #000;
            position: relative;
        }
        .eye-container.left {
            border-right: none;
        }
        .eye-container.right {
            border-left: none;
        }
        .eye-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: transform 0.1s ease-out;
            transform-origin: center center;
        }
        .eye-container.left img {
            transform: translateX(var(--left-offset, 0px)) scale(var(--image-scale, 1.0));
        }
        .eye-container.right img {
            transform: translateX(var(--right-offset, 0px)) scale(var(--image-scale, 1.0));
        }
        /* Control Panel (hidden by default, can be toggled) */
        .control-panel {
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 15px;
            border-radius: 10px;
            z-index: 1000;
            font-size: 12px;
            max-width: 200px;
            display: none;
        }
        .control-panel.visible {
            display: block;
        }
        .control-panel h3 {
            margin-bottom: 10px;
            font-size: 14px;
        }
        .control-panel .status {
            padding: 5px;
            margin: 5px 0;
            border-radius: 5px;
            font-size: 11px;
        }
        .status.disconnected {
            background: rgba(204, 51, 51, 0.5);
        }
        .status.connected {
            background: rgba(51, 204, 51, 0.5);
        }
        .control-panel button {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-start {
            background: #667eea;
            color: white;
        }
        .btn-stop {
            background: #f56565;
            color: white;
        }
        .toggle-panel {
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            z-index: 1001;
            font-size: 12px;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 18px;
            text-align: center;
        }
        /* Force landscape orientation */
        @media screen and (orientation: portrait) {
            body::before {
                content: "Пожалуйста, поверните устройство горизонтально";
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 30px;
                border-radius: 10px;
                z-index: 10000;
                font-size: 18px;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <!-- VR Display -->
    <div class="vr-container">
        <div class="eye-container left">
            <div class="loading" id="loadingLeft">Загрузка...</div>
            <img id="leftEye" src="/realsense_stream" alt="Left Eye" style="display: none;">
        </div>
        <div class="eye-container right">
            <div class="loading" id="loadingRight">Загрузка...</div>
            <img id="rightEye" src="/realsense_stream" alt="Right Eye" style="display: none;">
        </div>
    </div>
    
    <!-- Control Panel Toggle -->
    <button class="toggle-panel" onclick="toggleControlPanel()">⚙️</button>
    
    <!-- Control Panel -->
    <div class="control-panel" id="controlPanel">
        <h3>🤖 XLeRobotHead</h3>
        <div id="imuStatus" class="status disconnected">Disconnected</div>
        <div style="margin: 10px 0; font-size: 11px;">
            <div>Roll: <span id="roll">0.00°</span></div>
            <div>Pitch: <span id="pitch">0.00°</span></div>
            <div>Yaw: <span id="yaw">0.00°</span></div>
        </div>
        <button id="toggleBtn" class="btn-start" onclick="toggleStreaming()">Start Streaming</button>
        <button class="btn-start" onclick="enterFullscreen()" style="margin-top: 5px;">⛶ Fullscreen</button>
        <div style="margin-top: 15px; font-size: 11px;">
            <label style="display: block; margin-bottom: 5px; color: white;">VR Convergence:</label>
            <input type="range" id="convergenceSlider" min="-50" max="50" value="0" 
                   style="width: 100%; height: 20px;" 
                   oninput="updateConvergence(this.value)">
            <div style="text-align: center; font-size: 10px; color: #999; margin-top: 3px;">
                <span id="convergenceValue">0</span>px
            </div>
        </div>
        <div style="margin-top: 15px; font-size: 11px;">
            <label style="display: block; margin-bottom: 5px; color: white;">Image Scale:</label>
            <input type="range" id="scaleSlider" min="0.5" max="1.5" step="0.01" value="1.0" 
                   style="width: 100%; height: 20px;" 
                   oninput="updateImageScale(this.value)">
            <div style="text-align: center; font-size: 10px; color: #999; margin-top: 3px;">
                <span id="scaleValue">100</span>%
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 10px; color: #999;">
            <div id="platformInfo">Device sensor fusion</div>
            <div id="updateRate"></div>
        </div>
    </div>

    <script>
        // Load saved convergence value from localStorage
        let convergenceValue = 0;
        const savedConvergence = localStorage.getItem('vrConvergence');
        if (savedConvergence !== null) {
            convergenceValue = parseFloat(savedConvergence);
            const slider = document.getElementById('convergenceSlider');
            if (slider) {
                slider.value = convergenceValue;
            }
        }
        
        // Load saved image scale value from localStorage
        let imageScaleValue = 1.0;
        const savedScale = localStorage.getItem('vrImageScale');
        if (savedScale !== null) {
            imageScaleValue = parseFloat(savedScale);
            const slider = document.getElementById('scaleSlider');
            if (slider) {
                slider.value = imageScaleValue;
            }
        }
        
        // Update convergence (image offset for each eye)
        function updateConvergence(value) {
            convergenceValue = parseFloat(value);
            const root = document.documentElement;
            // Left eye: shift right (positive offset)
            // Right eye: shift left (negative offset)
            root.style.setProperty('--left-offset', convergenceValue + 'px');
            root.style.setProperty('--right-offset', (-convergenceValue) + 'px');
            
            // Update display
            const valueDisplay = document.getElementById('convergenceValue');
            if (valueDisplay) {
                valueDisplay.textContent = convergenceValue;
            }
            
            // Save to localStorage
            localStorage.setItem('vrConvergence', convergenceValue);
        }
        
        // Update image scale
        function updateImageScale(value) {
            imageScaleValue = parseFloat(value);
            const root = document.documentElement;
            root.style.setProperty('--image-scale', imageScaleValue);
            
            // Update display (show as percentage)
            const valueDisplay = document.getElementById('scaleValue');
            if (valueDisplay) {
                valueDisplay.textContent = Math.round(imageScaleValue * 100);
            }
            
            // Save to localStorage
            localStorage.setItem('vrImageScale', imageScaleValue);
        }
        
        // Initialize convergence and scale on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                updateConvergence(convergenceValue);
                updateImageScale(imageScaleValue);
            });
        } else {
            updateConvergence(convergenceValue);
            updateImageScale(imageScaleValue);
        }
        
        // Toggle control panel visibility
        function toggleControlPanel() {
            const panel = document.getElementById('controlPanel');
            if (panel) {
                panel.classList.toggle('visible');
            }
        }
        
        // Enter fullscreen mode
        function enterFullscreen() {
            const elem = document.body;
            if (elem.requestFullscreen) {
                elem.requestFullscreen().catch(err => {
                    console.log('Fullscreen request denied:', err);
                });
            } else if (elem.webkitRequestFullscreen) { // Safari
                elem.webkitRequestFullscreen();
            } else if (elem.mozRequestFullScreen) { // Firefox
                elem.mozRequestFullScreen();
            } else if (elem.msRequestFullscreen) { // IE/Edge
                elem.msRequestFullscreen();
            } else if (elem.webkitEnterFullscreen) { // iOS Safari
                elem.webkitEnterFullscreen();
            }
        }
        
        // Auto-enter fullscreen on first user interaction
        let fullscreenRequested = false;
        function requestFullscreenOnInteraction() {
            if (!fullscreenRequested) {
                fullscreenRequested = true;
                enterFullscreen();
            }
        }
        
        // Add event listeners for user interaction
        document.addEventListener('click', requestFullscreenOnInteraction, { once: true });
        document.addEventListener('touchstart', requestFullscreenOnInteraction, { once: true });
        
        // Lock screen orientation to landscape
        if (screen.orientation && screen.orientation.lock) {
            screen.orientation.lock('landscape').catch(() => {
                console.log('Could not lock orientation');
            });
        }
        
        // Detect platform
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || 
                     (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        const isAndroid = /Android/.test(navigator.userAgent);
        
        // Update platform info
        const platformInfo = document.getElementById('platformInfo');
        if (platformInfo) {
            if (isIOS) {
                platformInfo.textContent = 'iOS sensor fusion';
            } else if (isAndroid) {
                platformInfo.textContent = 'Android sensor fusion';
            } else {
                platformInfo.textContent = 'Device sensor fusion';
            }
        }
        
        // IMU WebSocket
        let ws = null;
        let isStreaming = false;
        let updateCount = 0;
        let lastRateUpdate = Date.now();
        
        function updateIMUStatus(connected) {
            const statusEl = document.getElementById('imuStatus');
            if (statusEl) {
                statusEl.textContent = connected ? 'Connected ✓' : 'Disconnected';
                statusEl.className = 'status ' + (connected ? 'connected' : 'disconnected');
            }
        }
        
        function updateRate() {
            const now = Date.now();
            const elapsed = (now - lastRateUpdate) / 1000;
            if (elapsed >= 1.0) {
                const rate = (updateCount / elapsed).toFixed(1);
                document.getElementById('updateRate').textContent = rate + ' Hz';
                updateCount = 0;
                lastRateUpdate = now;
            }
        }
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                updateIMUStatus(true);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateIMUStatus(false);
                if (isStreaming) {
                    setTimeout(connectWebSocket, 2000);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }
        
        function handleOrientation(event) {
            const alpha = event.alpha || 0;
            const beta = event.beta || 0;
            const gamma = event.gamma || 0;
            
            document.getElementById('roll').textContent = gamma.toFixed(2) + '°';
            document.getElementById('pitch').textContent = beta.toFixed(2) + '°';
            document.getElementById('yaw').textContent = alpha.toFixed(2) + '°';
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    mode: 'fused',
                    roll: gamma,
                    pitch: beta,
                    yaw: alpha
                }));
            }
            
            updateCount++;
            updateRate();
        }
        
        async function toggleStreaming() {
            const btn = document.getElementById('toggleBtn');
            
            if (!isStreaming) {
                // Check if DeviceOrientationEvent is supported
                if (typeof DeviceOrientationEvent === 'undefined') {
                    alert('Device orientation is not supported on this device/browser');
                    return;
                }
                
                // Request permissions (iOS 13+ requires explicit permission)
                if (isIOS && typeof DeviceOrientationEvent.requestPermission === 'function') {
                    try {
                        const permission = await DeviceOrientationEvent.requestPermission();
                        if (permission !== 'granted') {
                            alert('Permission denied for device orientation. Please allow access in Settings.');
                            return;
                        }
                    } catch (error) {
                        alert('Error requesting permission: ' + error);
                        return;
                    }
                }
                
                // Android and other platforms: check if orientation is available
                // On some Android devices, orientation might not be available immediately
                if (!isIOS) {
                    // Try to detect if orientation is available
                    let orientationAvailable = false;
                    const testHandler = () => {
                        orientationAvailable = true;
                        window.removeEventListener('deviceorientation', testHandler);
                    };
                    window.addEventListener('deviceorientation', testHandler);
                    
                    // Wait a bit to see if we get orientation data
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    if (!orientationAvailable && isAndroid) {
                        console.warn('Device orientation may not be available. Make sure you are using HTTPS.');
                    }
                }
                
                connectWebSocket();
                window.addEventListener('deviceorientation', handleOrientation);
                
                // Start video stream for both eyes
                const leftEye = document.getElementById('leftEye');
                const rightEye = document.getElementById('rightEye');
                const loadingLeft = document.getElementById('loadingLeft');
                const loadingRight = document.getElementById('loadingRight');
                const timestamp = new Date().getTime();
                
                if (leftEye && rightEye) {
                    // Use same stream for both eyes (monoscopic VR)
                    // For stereoscopic VR, you could use different endpoints
                    leftEye.src = '/realsense_stream?' + timestamp;
                    rightEye.src = '/realsense_stream?' + timestamp;
                    
                    leftEye.onload = () => {
                        leftEye.style.display = 'block';
                        if (loadingLeft) loadingLeft.style.display = 'none';
                    };
                    rightEye.onload = () => {
                        rightEye.style.display = 'block';
                        if (loadingRight) loadingRight.style.display = 'none';
                    };
                }
                
                isStreaming = true;
                btn.textContent = 'Stop Streaming';
                btn.className = 'btn-stop';
                lastRateUpdate = Date.now();
                updateCount = 0;
            } else {
                window.removeEventListener('deviceorientation', handleOrientation);
                if (ws) {
                    ws.close();
                }
                
                // Stop video stream
                const leftEye = document.getElementById('leftEye');
                const rightEye = document.getElementById('rightEye');
                const loadingLeft = document.getElementById('loadingLeft');
                const loadingRight = document.getElementById('loadingRight');
                
                if (leftEye) {
                    leftEye.src = '';
                    leftEye.style.display = 'none';
                    if (loadingLeft) loadingLeft.style.display = 'block';
                }
                if (rightEye) {
                    rightEye.src = '';
                    rightEye.style.display = 'none';
                    if (loadingRight) loadingRight.style.display = 'block';
                }
                
                isStreaming = false;
                btn.textContent = 'Start Streaming';
                btn.className = 'btn-start';
                updateIMUStatus(false);
                document.getElementById('updateRate').textContent = '';
            }
        }
    </script>
</body>
</html>"""
    
    def __init__(self, camera_id=0, enable_camera=False):
        """
        Initialize the server
        
        Args:
            camera_id: Camera device ID (default: 0)
            enable_camera: If True, automatically start camera capture (default: True)
        """
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        
        # Calibration offsets (initial angles at connection time)
        self.offset_roll = 0.0
        self.offset_pitch = 0.0
        self.offset_yaw = 0.0
        self.calibrated = False
        
        # Previous angles for smooth wrapping (store raw relative angles before normalization)
        self.prev_raw_roll = 0.0
        self.prev_raw_pitch = 0.0
        self.prev_raw_yaw = 0.0
        self.prev_norm_roll = 0.0
        self.prev_norm_pitch = 0.0
        self.prev_norm_yaw = 0.0
        
        # Track consecutive boundary hits to detect stuck angles
        self.boundary_count_roll = 0
        self.boundary_count_pitch = 0
        self.boundary_count_yaw = 0
        
        # Frame storage for external frames
        self.current_frame = None
        
        # Camera state
        self.camera_id = camera_id
        self.camera = None
        self.camera_thread = None
        self.camera_running = False
        self.enable_camera = enable_camera
        
        # Server state
        self.server_thread = None
        self.server_running = False
        self.runner = None
    
    @staticmethod
    def get_local_ip():
        """Get the local IP address of this computer"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    
    @staticmethod
    def create_self_signed_cert():
        """Create a self-signed certificate for HTTPS"""
        try:
            from OpenSSL import crypto
            
            k = crypto.PKey()
            k.generate_key(crypto.TYPE_RSA, 2048)
            
            cert = crypto.X509()
            cert.get_subject().C = "US"
            cert.get_subject().ST = "State"
            cert.get_subject().L = "City"
            cert.get_subject().O = "OrientationApp"
            cert.get_subject().OU = "OrientationApp"
            cert.get_subject().CN = PhoneServer.get_local_ip()
            cert.set_serial_number(1000)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(365*24*60*60)
            cert.set_issuer(cert.get_subject())
            cert.set_pubkey(k)
            cert.sign(k, 'sha256')
            
            with open("cert.pem", "wb") as f:
                f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            
            with open("key.pem", "wb") as f:
                f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
            
            print("✓ SSL certificate created successfully")
            return True
        except ImportError:
            print("\n⚠ pyOpenSSL not installed. Installing it now...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'pyOpenSSL'])
            print("✓ pyOpenSSL installed. Please run the script again.")
            return False
    
    def update_frame(self, frame: np.ndarray):
        """
        Update the current frame from external source.
        Note: This will be overridden by camera frames if camera is enabled.
        
        Args:
            frame: numpy array of uint8, shape (H, W, 3) in BGR format
        """
        if frame is not None and isinstance(frame, np.ndarray):
            # Only update if camera is not running (to avoid conflicts)
            if not self.camera_running:
                # Make a copy to avoid issues with external modifications
                self.current_frame = frame.copy()
    
    def get_current_frame(self):
        """Get the latest frame"""
        return self.current_frame.copy() if self.current_frame is not None else None
    
    def _camera_capture_loop(self):
        """Internal method to capture frames from camera in a separate thread"""
        print(f"Starting camera capture from device {self.camera_id}...")
        
        try:
            self.camera = cv2.VideoCapture(self.camera_id)
            if not self.camera.isOpened():
                print(f"⚠ Warning: Could not open camera {self.camera_id}")
                self.camera_running = False
                return
            
            # Set camera properties for better performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            print(f"✓ Camera {self.camera_id} opened successfully")
            
            while self.camera_running:
                ret, frame = self.camera.read()
                if ret:
                    # Frame is in BGR format from cv2
                    self.current_frame = frame
                else:
                    print("⚠ Warning: Failed to read frame from camera")
                    break
                    
        except Exception as e:
            print(f"⚠ Camera error: {e}")
        finally:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            self.camera_running = False
            print("Camera capture stopped")
    
    def start_camera(self, camera_id=None):
        """
        Start camera capture in a separate thread.
        
        Args:
            camera_id: Camera device ID (if None, uses self.camera_id)
        """
        if self.camera_running:
            print("Camera is already running!")
            return
        
        if camera_id is not None:
            self.camera_id = camera_id
        
        self.camera_running = True
        self.camera_thread = threading.Thread(
            target=self._camera_capture_loop,
            daemon=True
        )
        self.camera_thread.start()
    
    def stop_camera(self):
        """Stop camera capture"""
        if not self.camera_running:
            print("Camera is not running!")
            return
        
        self.camera_running = False
        
        # Wait for thread to finish
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=2)
        
        print("Camera stopped")
    
    @staticmethod
    def normalize_angle(angle, prev_raw_angle, prev_norm_angle, boundary_count=0, min_val=-90, max_val=90):
        """
        Normalize angle to range [min_val, max_val] with smooth unwrapping.
        Uses previous raw and normalized angles to detect boundary crossings and unwrap smoothly.
        
        Args:
            angle: Current raw angle value
            prev_raw_angle: Previous raw angle value (for detecting direction)
            prev_norm_angle: Previous normalized angle value (for boundary detection)
            boundary_count: Number of consecutive times angle was at boundary
            min_val: Minimum angle value (default: -90)
            max_val: Maximum angle value (default: +90)
        
        Returns:
            Tuple of (normalized angle, updated boundary_count)
        """
        # Normalize to -180..+180 range first (handle any angle value)
        angle = ((angle + 180) % 360) - 180
        prev_raw_normalized = ((prev_raw_angle + 180) % 360) - 180
        
        # Unwrap: if there's a large jump, it might be due to wrapping
        # Adjust angle to be closer to previous value
        diff = angle - prev_raw_normalized
        if diff > 180:
            angle -= 360
        elif diff < -180:
            angle += 360
        
        # Detect if we're stuck at boundary and need to unwrap
        # Check if previous normalized was at boundary (with tolerance)
        at_max_boundary = abs(prev_norm_angle - max_val) < 1.0
        at_min_boundary = abs(prev_norm_angle - min_val) < 1.0
        
        # Calculate direction of movement from raw angles
        raw_diff = angle - prev_raw_normalized
        
        # Check if current angle will be at boundary after clamping
        will_be_at_max = angle >= max_val - 0.1
        will_be_at_min = angle <= min_val + 0.1
        
        # Update boundary count
        if will_be_at_max or will_be_at_min:
            boundary_count += 1
        else:
            boundary_count = 0  # Reset if not at boundary
        
        # If stuck at boundary for multiple frames, force unwrapping
        force_unwrap = boundary_count >= 2
        
        # If at max boundary and angle is at or above max, unwrap to negative side
        if (at_max_boundary or will_be_at_max) and (raw_diff > 0.1 or angle > max_val or force_unwrap):
            excess = max(0, angle - max_val)
            angle = min_val + excess
            # Limit unwrapping to prevent going too far past center
            if angle > 0:
                angle = min(angle, 0)  # Don't go positive
            if force_unwrap:
                boundary_count = 0  # Reset after forced unwrap
        # If at min boundary and angle is at or below min, unwrap to positive side
        elif (at_min_boundary or will_be_at_min) and (raw_diff < -0.1 or angle < min_val or force_unwrap):
            excess = max(0, min_val - angle)
            angle = max_val - excess
            # Limit unwrapping to prevent going too far past center
            if angle < 0:
                angle = max(angle, 0)  # Don't go negative
            if force_unwrap:
                boundary_count = 0  # Reset after forced unwrap
        
        # Now clamp to desired range
        angle = max(min_val, min(max_val, angle))
        return angle, boundary_count
    
    def get_angles(self):
        """
        Get current orientation angles relative to connection time (calibrated).
        All angles are normalized to -90..+90 degrees range with smooth wrapping.
        
        Returns:
            dict: Dictionary with 'roll', 'pitch', 'yaw' in degrees (relative to initial position, normalized to -90..+90)
        """
        # Calculate relative angles (raw, before normalization)
        rel_roll = self.roll - self.offset_roll
        rel_pitch = self.pitch - self.offset_pitch
        rel_yaw = self.yaw - self.offset_yaw
        
        # Normalize all angles to -90..+90 range with smooth wrapping
        # Pass both raw previous angle and normalized previous angle for better unwrapping
        norm_roll, self.boundary_count_roll = self.normalize_angle(
            rel_roll, self.prev_raw_roll, self.prev_norm_roll, self.boundary_count_roll)
        norm_pitch, self.boundary_count_pitch = self.normalize_angle(
            rel_pitch, self.prev_raw_pitch, self.prev_norm_pitch, self.boundary_count_pitch)
        norm_yaw, self.boundary_count_yaw = self.normalize_angle(
            rel_yaw, self.prev_raw_yaw, self.prev_norm_yaw, self.boundary_count_yaw)
        
        # Update previous angles for next call (both raw and normalized)
        self.prev_raw_roll = rel_roll
        self.prev_raw_pitch = rel_pitch
        self.prev_raw_yaw = rel_yaw
        self.prev_norm_roll = norm_roll
        self.prev_norm_pitch = norm_pitch
        self.prev_norm_yaw = norm_yaw
        
        return {
            'roll': norm_roll,
            'pitch': norm_pitch,
            'yaw': -norm_yaw
        }
    
    def reset_calibration(self):
        """
        Reset calibration offsets. Next connection will recalibrate.
        """
        self.offset_roll = 0.0
        self.offset_pitch = 0.0
        self.offset_yaw = 0.0
        self.calibrated = False
    
    def recalibrate(self):
        """
        Recalibrate using current position as new zero point.
        Sets current angles as new offset values.
        """
        if not self.calibrated:
            print("⚠ Cannot recalibrate: no calibration data available yet")
            return
        
        # Set current angles as new offset (making current position the new zero)
        self.offset_roll = self.roll
        self.offset_pitch = self.pitch
        self.offset_yaw = self.yaw
        
        # Reset previous angles tracking
        self.prev_raw_roll = 0.0
        self.prev_raw_pitch = 0.0
        self.prev_raw_yaw = 0.0
        self.prev_norm_roll = 0.0
        self.prev_norm_pitch = 0.0
        self.prev_norm_yaw = 0.0
        self.boundary_count_roll = 0
        self.boundary_count_pitch = 0
        self.boundary_count_yaw = 0
        
        print(f"\n✓ Recalibrated: New zero point set at Roll={self.offset_roll:.2f}°, Pitch={self.offset_pitch:.2f}°, Yaw={self.offset_yaw:.2f}°")
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections for IMU data"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        print(f"\nPhone connected from {request.remote}")
        
        # Reset calibration for new connection
        self.calibrated = False
        self.offset_roll = 0.0
        self.offset_pitch = 0.0
        self.offset_yaw = 0.0
        
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    
                    # Get raw orientation values
                    raw_roll = data.get('roll', 0.0)
                    raw_pitch = data.get('pitch', 0.0)
                    raw_yaw = data.get('yaw', 0.0)
                    
                    # Calibrate on first data received
                    if not self.calibrated:
                        self.offset_roll = raw_roll
                        self.offset_pitch = raw_pitch
                        self.offset_yaw = raw_yaw
                        self.calibrated = True
                        print(f"\n✓ Calibration set: Roll={self.offset_roll:.2f}°, Pitch={self.offset_pitch:.2f}°, Yaw={self.offset_yaw:.2f}°")
                    
                    # Store raw values
                    self.roll = raw_roll
                    self.pitch = raw_pitch
                    self.yaw = raw_yaw
                    
                    # Get normalized angles (same as get_angles() returns)
                    angles = self.get_angles()
                    
                    print(f"\r[Normalized] Roll: {angles['roll']:7.2f}° | Pitch: {angles['pitch']:7.2f}° | Yaw: {angles['yaw']:7.2f}°", end='')
                    
                    # Add your custom processing here
                    # You can access self.roll, self.pitch, self.yaw (raw values)
                    # Or use get_angles() for relative values
                    
                except json.JSONDecodeError:
                    print("Invalid JSON received")
            elif msg.type == web.WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')
        
        # Reset calibration on disconnect
        self.calibrated = False
        self.offset_roll = 0.0
        self.offset_pitch = 0.0
        self.offset_yaw = 0.0
        self.prev_raw_roll = 0.0
        self.prev_raw_pitch = 0.0
        self.prev_raw_yaw = 0.0
        self.prev_norm_roll = 0.0
        self.prev_norm_pitch = 0.0
        self.prev_norm_yaw = 0.0
        self.boundary_count_roll = 0
        self.boundary_count_pitch = 0
        self.boundary_count_yaw = 0
        print("\nPhone disconnected (calibration reset)")
        return ws
    
    async def index_handler(self, request):
        """Handle main page requests"""
        return web.Response(text=self.HTML_PAGE, content_type='text/html')
    
    async def realsense_stream_handler(self, request):
        """MJPEG stream handler for video frames (VR mode - landscape orientation)"""
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'multipart/x-mixed-replace; boundary=frame'
        await response.prepare(request)
        
        print(f"Video stream started for {request.remote}")
        
        # Create placeholder for when no frame is available (landscape orientation)
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(placeholder, 'Waiting for frames...', (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, placeholder_buffer = cv2.imencode('.jpg', placeholder)
        
        while True:
            frame = self.get_current_frame()
            if frame is not None:
                # Frame is expected to be in BGR format (uint8)
                # Ensure it's the right format
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                
                # Ensure landscape orientation for VR
                # If frame is portrait (height > width), rotate it
                h, w = frame.shape[:2]
                if h > w:
                    # Rotate 90 degrees clockwise to make it landscape
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                    h, w = frame.shape[:2]  # Update dimensions after rotation
                
                # Resize maintaining aspect ratio (max dimension for quality)
                # Target max width: 1920, max height: 1080 for better quality
                max_width = 1920
                max_height = 1080
                
                # Calculate scaling factor to fit within max dimensions while preserving aspect ratio
                scale_w = max_width / w if w > max_width else 1.0
                scale_h = max_height / h if h > max_height else 1.0
                scale = min(scale_w, scale_h)  # Use smaller scale to fit both dimensions
                
                if scale < 1.0:
                    new_width = int(w * scale)
                    new_height = int(h * scale)
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                
                # Encode frame as JPEG with higher quality for VR
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                
                await response.write(b'--frame\r\n')
                await response.write(b'Content-Type: image/jpeg\r\n\r\n')
                await response.write(buffer.tobytes())
                await response.write(b'\r\n')
            else:
                # Send placeholder if no frame available
                await response.write(b'--frame\r\n')
                await response.write(b'Content-Type: image/jpeg\r\n\r\n')
                await response.write(placeholder_buffer.tobytes())
                await response.write(b'\r\n')
            
            await asyncio.sleep(1/30)  # ~30 FPS
    
    def create_app(self):
        """Create aiohttp web application"""
        app = web.Application()
        app.router.add_get('/', self.index_handler)
        app.router.add_get('/ws', self.websocket_handler)
        app.router.add_get('/realsense_stream', self.realsense_stream_handler)
        return app
    
    def _run_server(self, host='0.0.0.0', port=8443):
        """Internal method to run server in event loop"""
        async def start():
            if not os.path.exists('cert.pem') or not os.path.exists('key.pem'):
                print("Creating SSL certificate...")
                if not self.create_self_signed_cert():
                    return
            
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain('cert.pem', 'key.pem')
            
            local_ip = self.get_local_ip()
            print("\n" + "=" * 70)
            print("XLeRobotHead - IMU & RealSense Server")
            print("=" * 70)
            print(f"✓ Server started with HTTPS support!")
            print(f"\n📱 Mobile Device: Open browser and go to:")
            print(f"   https://{local_ip}:{port}\n")
            print(f"   • iOS: Use Safari")
            print(f"   • Android: Use Chrome or Firefox")
            print(f"\nFeatures available:")
            if self.enable_camera and self.camera_running:
                print(f"  • Video Frame Streaming (camera {self.camera_id})")
            else:
                print(f"  • Video Frame Streaming (external frames)")
            print(f"  • Mobile IMU/Orientation Data (iOS & Android)")
            print("=" * 70)
            print("Waiting for connection...\n")
            
            app = self.create_app()
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
            await site.start()
            
            # Store runner for cleanup
            self.runner = runner
            
            # Keep running
            while self.server_running:
                await asyncio.sleep(1)
            
            # Cleanup when stopping
            await runner.cleanup()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(start())
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            loop.close()
    
    def run(self, host='0.0.0.0', port=8443, background=True):
        """
        Run the server.
        
        Args:
            host: Server host (default: '0.0.0.0')
            port: Server port (default: 8443)
            background: If True, run in background thread (default: True)
        """
        if self.server_running:
            print("Server is already running!")
            return
        
        self.server_running = True
        
        # Start camera if enabled
        if self.enable_camera:
            self.start_camera()
        
        if background:
            # Run in background thread
            self.server_thread = threading.Thread(
                target=self._run_server,
                args=(host, port),
                daemon=True
            )
            self.server_thread.start()
            print("Server started in background thread")
        else:
            # Run in current thread (blocking)
            try:
                self._run_server(host, port)
            except KeyboardInterrupt:
                print("\n\nServer stopped by user")
            finally:
                self.server_running = False
                if self.enable_camera:
                    self.stop_camera()
    
    def stop(self):
        """Stop the server and camera"""
        if not self.server_running:
            print("Server is not running!")
            return
        
        self.server_running = False
        
        # Stop camera
        if self.camera_running:
            self.stop_camera()
        
        # Wait for thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=3)
        
        print("Server stopped")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phone Server for IMU and Camera Streaming')
    parser.add_argument('--camera-id', type=int, default=0, help='Camera device ID (default: 0)')
    parser.add_argument('--no-camera', action='store_true', help='Disable automatic camera capture')
    parser.add_argument('--port', type=int, default=8443, help='Server port (default: 8443)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    
    args = parser.parse_args()
    
    server = PhoneServer(camera_id=args.camera_id, enable_camera=not args.no_camera)
    server.run(host=args.host, port=args.port, background=False)


if __name__ == "__main__":
    main()
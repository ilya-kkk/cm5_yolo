#!/usr/bin/env python3
"""
Status Web Service for YOLO Camera Stream
Shows connection status and allows manual control of libcamera-vid
"""

from flask import Flask, render_template_string, Response, jsonify
import subprocess
import threading
import time
import socket
import os

app = Flask(__name__)

class StreamStatusMonitor:
    def __init__(self):
        self.libcamera_running = False
        self.udp_port_open = False
        self.last_check = time.time()
        
    def check_libcamera_status(self):
        """Check if libcamera-vid is running"""
        try:
            result = subprocess.run(['pgrep', 'libcamera-vid'], 
                                  capture_output=True, text=True)
            self.libcamera_running = result.returncode == 0
        except:
            self.libcamera_running = False
    
    def check_udp_port(self):
        """Check if UDP port 5000 is receiving data"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.bind(('127.0.0.1', 5000))
            
            # Try to receive data
            try:
                data, addr = sock.recvfrom(1024)
                self.udp_port_open = len(data) > 0
            except socket.timeout:
                self.udp_port_open = False
            
            sock.close()
        except:
            self.udp_port_open = False
    
    def get_status(self):
        """Get current status"""
        self.check_libcamera_status()
        self.check_udp_port()
        self.last_check = time.time()
        
        return {
            "libcamera_running": self.libcamera_running,
            "udp_port_open": self.udp_port_open,
            "last_check": self.last_check,
            "overall_status": "active" if (self.libcamera_running and self.udp_port_open) else "inactive"
        }

# Global status monitor
status_monitor = StreamStatusMonitor()

@app.route('/')
def index():
    """Main page with status information"""
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YOLO Camera Stream Status</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                max-width: 800px;
                width: 100%;
                text-align: center;
            }
            
            h1 {
                color: #333;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            
            .status-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 15px;
                border-left: 4px solid #28a745;
                text-align: left;
            }
            
            .status-card.error {
                border-left-color: #dc3545;
            }
            
            .status-card.warning {
                border-left-color: #ffc107;
            }
            
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 10px;
            }
            
            .status-online {
                background: #28a745;
            }
            
            .status-offline {
                background: #dc3545;
            }
            
            .status-warning {
                background: #ffc107;
            }
            
            .controls {
                display: flex;
                gap: 15px;
                justify-content: center;
                flex-wrap: wrap;
                margin: 30px 0;
            }
            
            .btn {
                padding: 15px 30px;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }
            
            .btn-primary {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }
            
            .btn-success {
                background: linear-gradient(45deg, #28a745, #20c997);
                color: white;
            }
            
            .btn-danger {
                background: linear-gradient(45deg, #dc3545, #c82333);
                color: white;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }
            
            .info {
                background: #e3f2fd;
                padding: 20px;
                border-radius: 15px;
                margin: 30px 0;
                border-left: 4px solid #2196f3;
                text-align: left;
            }
            
            .log {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 15px;
                margin: 20px 0;
                border: 1px solid #dee2e6;
                text-align: left;
                max-height: 300px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 14px;
            }
            
            .refresh-info {
                text-align: center;
                color: #666;
                font-size: 14px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎥 YOLO Camera Stream Status</h1>
            
            <div class="status-grid">
                <div class="status-card" id="libcamera-status">
                    <h3>📹 libcamera-vid</h3>
                    <p><span class="status-indicator" id="libcamera-indicator"></span>
                       <span id="libcamera-text">Проверка...</span></p>
                </div>
                
                <div class="status-card" id="udp-status">
                    <h3>📡 UDP Порт 5000</h3>
                    <p><span class="status-indicator" id="udp-indicator"></span>
                       <span id="udp-text">Проверка...</span></p>
                </div>
                
                <div class="status-card" id="overall-status">
                    <h3>✅ Общий статус</h3>
                    <p><span class="status-indicator" id="overall-indicator"></span>
                       <span id="overall-text">Проверка...</span></p>
                </div>
            </div>
            
            <div class="controls">
                <button class="btn btn-success" onclick="startLibcamera()">🚀 Запустить libcamera-vid</button>
                <button class="btn btn-danger" onclick="stopLibcamera()">🛑 Остановить libcamera-vid</button>
                <button class="btn btn-primary" onclick="refreshStatus()">🔄 Обновить статус</button>
            </div>
            
            <div class="info">
                <h3>📋 Инструкции по запуску:</h3>
                <ol>
                    <li><strong>Запустите libcamera-vid:</strong> Нажмите кнопку "Запустить libcamera-vid" выше</li>
                    <li><strong>Проверьте статус:</strong> Нажмите "Обновить статус"</li>
                    <li><strong>Откройте веб-интерфейс:</strong> <code>http://192.168.0.164:8080</code></li>
                    <li><strong>Для просмотра с телефона:</strong> Откройте в браузере телефона тот же адрес</li>
                </ol>
            </div>
            
            <div class="log" id="log">
                <h3>📝 Лог событий:</h3>
                <div id="log-content">
                    <div>Система готова к работе...</div>
                </div>
            </div>
            
            <div class="refresh-info">
                Статус автоматически обновляется каждые 5 секунд
            </div>
        </div>
        
        <script>
            function updateStatus() {
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        // Update libcamera status
                        const libcameraIndicator = document.getElementById('libcamera-indicator');
                        const libcameraText = document.getElementById('libcamera-text');
                        const libcameraCard = document.getElementById('libcamera-status');
                        
                        if (data.libcamera_running) {
                            libcameraIndicator.className = 'status-indicator status-online';
                            libcameraText.textContent = 'Запущен';
                            libcameraCard.className = 'status-card';
                        } else {
                            libcameraIndicator.className = 'status-indicator status-offline';
                            libcameraText.textContent = 'Остановлен';
                            libcameraCard.className = 'status-card error';
                        }
                        
                        // Update UDP status
                        const udpIndicator = document.getElementById('udp-indicator');
                        const udpText = document.getElementById('udp-text');
                        const udpCard = document.getElementById('udp-status');
                        
                        if (data.udp_port_open) {
                            udpIndicator.className = 'status-indicator status-online';
                            udpText.textContent = 'Активен';
                            udpCard.className = 'status-card';
                        } else {
                            udpIndicator.className = 'status-indicator status-offline';
                            udpText.textContent = 'Неактивен';
                            udpCard.className = 'status-card error';
                        }
                        
                        // Update overall status
                        const overallIndicator = document.getElementById('overall-indicator');
                        const overallText = document.getElementById('overall-text');
                        const overallCard = document.getElementById('overall-status');
                        
                        if (data.overall_status === 'active') {
                            overallIndicator.className = 'status-indicator status-online';
                            overallText.textContent = 'Система работает';
                            overallCard.className = 'status-card';
                        } else {
                            overallIndicator.className = 'status-indicator status-warning';
                            overallText.textContent = 'Требуется настройка';
                            overallCard.className = 'status-card warning';
                        }
                    })
                    .catch(error => {
                        addLog('Ошибка получения статуса: ' + error.message);
                    });
            }
            
            function startLibcamera() {
                addLog('Запуск libcamera-vid...');
                
                fetch('/start_libcamera', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            addLog('✅ libcamera-vid запущен успешно');
                        } else {
                            addLog('❌ Ошибка запуска: ' + data.error);
                        }
                        setTimeout(updateStatus, 2000);
                    })
                    .catch(error => {
                        addLog('❌ Ошибка: ' + error.message);
                    });
            }
            
            function stopLibcamera() {
                addLog('Остановка libcamera-vid...');
                
                fetch('/stop_libcamera', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            addLog('✅ libcamera-vid остановлен');
                        } else {
                            addLog('❌ Ошибка остановки: ' + data.error);
                        }
                        setTimeout(updateStatus, 2000);
                    })
                    .catch(error => {
                        addLog('❌ Ошибка: ' + error.message);
                    });
            }
            
            function refreshStatus() {
                addLog('Обновление статуса...');
                updateStatus();
            }
            
            function addLog(message) {
                const logContent = document.getElementById('log-content');
                const timestamp = new Date().toLocaleTimeString();
                const logEntry = document.createElement('div');
                logEntry.innerHTML = `<span style="color: #666;">[${timestamp}]</span> ${message}`;
                logContent.appendChild(logEntry);
                
                // Auto-scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
                
                // Keep only last 50 entries
                while (logContent.children.length > 50) {
                    logContent.removeChild(logContent.firstChild);
                }
            }
            
            // Initial setup
            updateStatus();
            
            // Auto-refresh every 5 seconds
            setInterval(updateStatus, 5000);
            
            // Add initial log
            addLog('Система мониторинга запущена');
        </script>
    </body>
    </html>
    """
    return html_template

@app.route('/status')
def get_status():
    """Get current system status"""
    return jsonify(status_monitor.get_status())

@app.route('/start_libcamera', methods=['POST'])
def start_libcamera():
    """Start libcamera-vid streaming"""
    try:
        # Kill any existing libcamera-vid processes
        subprocess.run(['pkill', 'libcamera-vid'], capture_output=True)
        time.sleep(1)
        
        # Start new libcamera-vid process
        cmd = [
            'libcamera-vid',
            '-t', '0',  # Run indefinitely
            '--codec', 'h264',
            '--width', '640',
            '--height', '480',
            '--framerate', '30',
            '--inline',
            '-o', 'udp://127.0.0.1:5000'
        ]
        
        # Start in background
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait a bit to see if it starts successfully
        time.sleep(2)
        
        if process.poll() is None:  # Process is still running
            return jsonify({"success": True, "message": "libcamera-vid started"})
        else:
            return jsonify({"success": False, "error": "Process failed to start"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/stop_libcamera', methods=['POST'])
def stop_libcamera():
    """Stop libcamera-vid streaming"""
    try:
        result = subprocess.run(['pkill', 'libcamera-vid'], capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({"success": True, "message": "libcamera-vid stopped"})
        else:
            return jsonify({"success": False, "error": "No processes found"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    status = status_monitor.get_status()
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "libcamera_running": status["libcamera_running"],
        "udp_port_open": status["udp_port_open"],
        "overall_status": status["overall_status"]
    })

def start_web_service():
    """Start the web service"""
    try:
        print("Starting status web service...")
        print("Web service will be available at: http://0.0.0.0:8080")
        print("Access the status page at: http://<CM5_IP>:8080")
        
        app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("Stopping web service...")
    except Exception as e:
        print(f"Error starting web service: {e}")

if __name__ == '__main__':
    start_web_service() 
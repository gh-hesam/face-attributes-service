#!/bin/bash

### 🛑 Stop All Running Services

echo "[INFO] Stopping input_service..."
pkill -f input_service.py || echo "input_service not running"

echo "[INFO] Stopping landmark_service..."
pkill -f landmark_service.py || echo "landmark_service not running"

echo "[INFO] Stopping agegender_service..."
pkill -f agegender_service.py || echo "agegender_service not running"

echo "[INFO] Stopping data_storage_service..."
pkill -f data_storage_service.py || echo "data_storage_service not running"

echo "[INFO] Stopping gradio_viewer..."
pkill -f gradio_viewer.py || echo "gradio_viewer not running"

### 🧹 Optional: Clear logs
read -p "Do you want to delete all log files? (y/n): " choice
if [ "$choice" = "y" ]; then
    rm -rf logs/*.log
    echo "[INFO] Logs deleted."
else
    echo "[INFO] Logs kept."
fi

### ✅ Done
echo "[✓] Cleanup complete. All services stopped."

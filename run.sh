#!/bin/bash

set -e

### 📦 Step 1: Setup Python Virtual Environment

echo "[INFO] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

### 🔄 Step 2: Upgrade pip and install requirements

echo "[INFO] Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

### ✅ Step 3: Start Services in Background (Logs go to log files)

mkdir -p logs

echo "[INFO] Starting input_service..."
nohup python input_service.py > logs/input.log 2>&1 &

echo "[INFO] Starting landmark_service..."
nohup python landmark_service.py > logs/landmark.log 2>&1 &

echo "[INFO] Starting agegender_service..."
nohup python agegender_service.py > logs/agegender.log 2>&1 &

echo "[INFO] Starting data_storage_service..."
nohup python data_storage_service.py > logs/storage.log 2>&1 &

echo "[INFO] Starting gradio_viewer (UI)..."
nohup python gradio_viewer.py > logs/viewer.log 2>&1 &

### ℹ️ Final Info
echo "[✓] All services started. Logs are in ./logs"
echo "[ℹ️] Make sure Redis is running! See below for install instructions."

### 🧠 Redis Setup (from DigitalOcean)
echo "\nTo install Redis on Ubuntu, run these commands:" 
echo "sudo apt update"
echo "sudo apt install redis-server"
echo "sudo systemctl enable redis-server.service"
echo "sudo systemctl start redis"
echo "sudo systemctl status redis"

echo "\nIf Redis is working, you're good to go!"

#  Face Analysis Pipeline

A modular microservice-based system that processes uploaded images to:

✅ Detect **faces**  
✅ Extract **facial landmarks**  
✅ Predict **age and gender**  
✅ Log everything  
✅ Save structured results (JSON + image) in a clean format

---


##  What This Project Does

This project takes in a raw image, processes it through multiple intelligent services, and outputs a structured `.json` file and the annotated image. For **each detected face**, it provides:

- **Facial landmarks** using MediaPipe
- **Bounding box** of the face
- **Predicted age and gender** using DeepFace
- **Per-face metadata** organized in a single file
- A **visual display** with landmarks and labels
- A **logging system** for full pipeline traceability

---

## ⚙️ How It Works

This system is built as a set of **microservices**, each responsible for a specific part of the image analysis pipeline. All services communicate through **Redis queues** and **gRPC**.

### 🧩 Services Overview

| Service               | Description                                              |
|-----------------------|----------------------------------------------------------|
| `input_service`       | Accepts and queues new images (uploads to Redis)        |
| `landmark_service`    | Detects faces and extracts landmarks using YOLO & MediaPipe |
| `agegender_service`   | Analyzes each face crop with DeepFace for age/gender     |
| `data_storage_service`| Merges all results and saves them as `.jpg` and `.json` |
| `logger_service`      | Logs every step and error across the pipeline           |
| `gradio_viewer`       | Interactive UI to view results and annotations          |

### 🛠 Technologies Used

- 🧠 **YOLOv8 (Ultralytics)** – for face detection  
- 👁️ **MediaPipe** – for facial landmark extraction  
- 👤 **DeepFace** – for age and gender analysis  
- ⚡ **gRPC** – for service-to-service communication  
- 🧰 **Redis** – for task queuing and temporary image storage  
- 💬 **Gradio** – for live result visualization  
- 📝 **Custom Logger** – for centralized logging of all services  

---

## 🚀 How to Run and Use

## first choice: instal and run manually
### 1. 📦 Install Requirements

```bash
pip install -r requirements.txt
```
Ensure the following are set up:
```bash
Python 3.8+

Redis server running locally

YOLOv8 model file available as model.pt in your working directory

```
3. 📤 Upload an Image

Use the input service (or write a small uploader script) to push an image into Redis. The pipeline will:

* Detect all faces
* Analyze each face
* Merge all data
* Save saved_data/<image_hash>.jpg and saved_data/<image_hash>.json

## second choise: ready to use bash scripts
### 1. Give it execute permission:
```bash 
chmod +x run.sh
```
### 2.run it 
```bash 
./run_everything.sh
```
and for stop the services:
```bash 
chmod +x stop_services.sh
./stop_services.sh
```

## Output Format

Each .json file looks like:
```bash
    {
    "timestamp": "...",
    "image_path": "saved_data/<image_hash>.jpg",
    "redis_key": "image:<hash>",
    "num_faces": 2,
    "faces": [
        {
        "face_index": 0,
        "box": { "x1": ..., "y1": ..., "x2": ..., "y2": ... },
        "landmarks": [ {"x": ..., "y": ...}, ... ],
        "agegender": { "age": 28, "gender": "male" }
        },
        ...
    ]
    }
```
# Results
![alt text](./images/1.png.png?raw=true "test image#1")
![alt text](./images/2.png.png?raw=true "test image#2")
![alt text](./images/3.png.png?raw=true "test image#3")
# TODO
- [ ] dockerize the project
- [ ] add result plotter service
- [ ] Replace DeepFace with a more accurate age/gender model

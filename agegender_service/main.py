import os
import cv2
import numpy as np
import redis
import time
import json
import grpc
from deepface import DeepFace
from datetime import datetime
from ultralytics import YOLO

import aggregator_pb2
import aggregator_pb2_grpc

# Config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", "localhost:50051")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
face_detector = YOLO("model.pt").to("cpu") #TODO use face detection only once for all servicess 

def parse_gender(gender_raw):
    if isinstance(gender_raw, str):
        return gender_raw.lower()
    if isinstance(gender_raw, dict):
        return max(gender_raw, key=gender_raw.get).lower()
    return "unknown"

def detect_faces(image):
    results = face_detector(image)[0]
    boxes = results.boxes.xyxy.cpu().numpy().astype(int)
    return boxes

def analyze_faces(image_bytes):
    image_np = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    boxes = detect_faces(image)
    results = []

    for idx, (x1, y1, x2, y2) in enumerate(boxes):
        face_crop = image[y1:y2, x1:x2]
        try:
            result = DeepFace.analyze(face_crop, actions=['age', 'gender'], enforce_detection=False)[0]
            age = int(result['age'])
            gender = parse_gender(result['gender'])

            results.append({
                "face_index": idx,
                "box": {"x1": int(x1),
                         "y1": int(y1), 
                         "x2": int(x2),
                           "y2": int(y2)},
                "agegender": {"age": age, "gender": gender}
            })
        except Exception as e:
            print(f"DeepFace failed on  {idx}: {e}")
            continue

    return results

def send_to_storage(image_bytes, redis_key, metadata_dict):
    try:
        r.set(redis_key, json.dumps(metadata_dict))
        with grpc.insecure_channel(GRPC_ADDRESS) as channel:
            stub = aggregator_pb2_grpc.AggregatorStub(channel)
            request = aggregator_pb2.FaceResult(
                time=datetime.utcnow().isoformat(),
                frame=image_bytes,
                redis_key=redis_key
            )
            response = stub.SaveFaceAttributes(request)
            print("age gender services :", response.response)
    except Exception as e:
        print(f"agegen Failed to send to storage: {e}")

def process_image(image_hash):
    image_bytes = r.get(f"image:{image_hash}")
    if image_bytes is None:
        print(f"not found key:{image_hash}")
        return

    start = time.time()
    face_data = analyze_faces(image_bytes)
    duration = time.time() - start

    metadata = {
        "num_faces": len(face_data),
        "faces": face_data,
        "processing_time_sec": round(duration, 3)
    }

    redis_key = f"combined:{image_hash}:agegender"
    send_to_storage(image_bytes, redis_key, metadata)

def main():
    print("Agegen service running...")
    while True:
        try:
            task = r.brpop("task:agegender", timeout=10)
            if task is None:
                continue
            _, image_hash_bytes = task
            image_hash = image_hash_bytes.decode()
            print(f"received task for {image_hash}")
            process_image(image_hash)
        except Exception as e:
            print(f"age gen  error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

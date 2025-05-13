import redis
import cv2
import numpy as np
import time
import os
from ultralytics import YOLO
import mediapipe as mp
import json
import grpc
from datetime import datetime

import aggregator_pb2
import aggregator_pb2_grpc

# Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", "localhost:50051")

r = redis.Redis.from_url(REDIS_URL)
face_detector = YOLO("model.pt").to("cpu")
mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)

def get_faces(image):
    results = face_detector(image)[0]
    boxes = results.boxes.xyxy.cpu().numpy().astype(int)
    return boxes

def get_landmarks(face_img):
    results = mp_face_mesh.process(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
    if results.multi_face_landmarks:
        return results.multi_face_landmarks[0].landmark
    return None

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
            print(" Landmark  status :", response.response)
    except Exception as e:
        print(f"failed to send to storage: {e}")

def main_loop():
    print("landmark detection dervice started")
    while True:
        try:
            key = r.rpop("task:landmark")
            if not key:
                time.sleep(0.5)
                continue

            key = key.decode()
            image_bytes = r.get(f"image:{key}")
            if not image_bytes:
                continue

            image_np = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            face_boxes = get_faces(image)
            all_faces_data = []

            for idx, (x1, y1, x2, y2) in enumerate(face_boxes):
                face_crop = image[y1:y2, x1:x2]
                landmarks = get_landmarks(face_crop)
                if not landmarks:
                    continue
                abs_landmarks = [{"x": int(lm.x * (x2 - x1) + x1), "y": int(lm.y * (y2 - y1) + y1)} for lm in landmarks]
                all_faces_data.append({
                    "face_index": idx,
                    "box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                    "landmarks": abs_landmarks
                })

            if not all_faces_data:
                print(f"no faces with landmarks found in {key}")
                continue

            redis_key = f"combined:{key}:landmarks"
            metadata = {
                "num_faces": len(all_faces_data),
                "faces": all_faces_data
            }

            send_to_storage(image_bytes, redis_key, metadata)
            r.delete(f"image:{key}")
        except Exception as e:
            print(f"lndmark error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main_loop()

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

from utils import aggregator_pb2
from utils import aggregator_pb2_grpc
from utils import logger

# Config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", "localhost:50051")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
face_detector = YOLO("model.pt").to("cpu")  # TODO: Share across services later

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

def analyze_faces(image_bytes, image_hash):
    image_np = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    boxes = detect_faces(image)
    logger.log_info(f"[AGEGEN] Detected {len(boxes)} face(s) for image {image_hash}")
    results = []

    for idx, (x1, y1, x2, y2) in enumerate(boxes):
        face_crop = image[y1:y2, x1:x2]
        try:
            result = DeepFace.analyze(face_crop, actions=['age', 'gender'], enforce_detection=False)[0]
            age = int(result['age'])
            gender = parse_gender(result['gender'])

            logger.log_info(f"[AGEGEN] Face {idx} — age: {age}, gender: {gender} (image: {image_hash})")

            results.append({
                "face_index": idx,
                "box": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                "agegender": {"age": age, "gender": gender}
            })
        except Exception as e:
            logger.log_error(f"[AGEGEN] DeepFace failed on face {idx} in {image_hash}: {e}")
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
            if response.response:
                logger.log_info(f"[AGEGEN] Sent to storage for key {redis_key}")
            else:
                logger.log_warning(f"[AGEGEN] Storage service returned failure for key {redis_key}")
    except Exception as e:
        logger.log_error(f"[AGEGEN] Failed to send to storage: {e}")

def process_image(image_hash):
    image_bytes = r.get(f"image:{image_hash}")
    if image_bytes is None:
        logger.log_warning(f"[AGEGEN] Image not found in Redis for key: {image_hash}")
        return

    start = time.time()
    face_data = analyze_faces(image_bytes, image_hash)
    duration = time.time() - start

    metadata = {
        "num_faces": len(face_data),
        "faces": face_data,
        "processing_time_sec": round(duration, 3)
    }

    redis_key = f"combined:{image_hash}:agegender"
    logger.log_info(f"[AGEGEN] Processed image {image_hash} in {duration:.2f}s")

    try:
        send_to_storage(image_bytes, redis_key, metadata)
        # Only delete if everything else above succeeded
        r.delete(f"image:{image_hash}")
        logger.log_info(f"[AGEGEN] Deleted image:{image_hash} from Redis after processing")
    except Exception as e:
        logger.log_error(f"[AGEGEN] Failed during final cleanup: {e}")

def main():
    logger.log_info("[AGEGEN] Age/Gender Detection Service started...")
    while True:
        try:
            task = r.brpop("task:agegender", timeout=10)
            if task is None:
                continue
            _, image_hash_bytes = task
            image_hash = image_hash_bytes.decode()
            logger.log_info(f"[AGEGEN] Received task for {image_hash}")
            process_image(image_hash)
        except Exception as e:
            logger.log_error(f"[AGEGEN] Main loop error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

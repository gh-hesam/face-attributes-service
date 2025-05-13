import grpc
from concurrent import futures
import redis
import os
import json
from datetime import datetime

from utils import aggregator_pb2
from utils import aggregator_pb2_grpc
from utils import logger

# Config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
SAVE_DIR = "saved_data"
os.makedirs(SAVE_DIR, exist_ok=True)

# Redis connection
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

class AggregatorService(aggregator_pb2_grpc.AggregatorServicer):
    def SaveFaceAttributes(self, request, context):
        try:
            redis_key = request.redis_key
            if not redis_key.startswith("combined:"):
                logger.log_warning(f"[STORAGE] Invalid redis_key format: {redis_key}")
                return aggregator_pb2.FaceResultResponse(response=False)

            image_hash = redis_key.split(":")[1]
            part_type = redis_key.split(":")[2]  # "landmarks" or "agegender"
            image_bytes = request.frame
            timestamp = request.time or datetime.utcnow().isoformat()

            # Save part to temporary merged Redis keys
            incoming_data_raw = r.get(redis_key)
            if incoming_data_raw is None:
                logger.log_error(f"[STORAGE] Redis key not found: {redis_key}")
                return aggregator_pb2.FaceResultResponse(response=False)

            r.set(f"merged:{image_hash}:{part_type}", incoming_data_raw)
            logger.log_info(f"[STORAGE] Received {part_type} data for image {image_hash}")

            # Check if both parts are ready
            part1 = r.get(f"merged:{image_hash}:landmarks")
            part2 = r.get(f"merged:{image_hash}:agegender")

            if not (part1 and part2):
                logger.log_info(f"[STORAGE] Only one part available for image {image_hash} — waiting...")
                return aggregator_pb2.FaceResultResponse(response=True)

            # Decode parts
            try:
                landmarks_data = json.loads(part1.decode())
                agegender_data = json.loads(part2.decode())
            except Exception as e:
                logger.log_error(f"[STORAGE] JSON decode error: {e}")
                return aggregator_pb2.FaceResultResponse(response=False)

            # Merge face-wise
            merged_faces = []
            for l_face in landmarks_data.get("faces", []):
                face_index = l_face.get("face_index")
                match = next(
                    (f for f in agegender_data.get("faces", []) if f.get("face_index") == face_index),
                    {}
                )
                merged_faces.append({
                    "face_index": face_index,
                    "box": l_face.get("box"),
                    "landmarks": l_face.get("landmarks"),
                    "agegender": match.get("agegender", {})
                })

            # Save image
            image_path = os.path.join(SAVE_DIR, f"{image_hash}.jpg")
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            # Save final JSON
            final_data = {
                "timestamp": timestamp,
                "image_path": image_path,
                "redis_key": f"image:{image_hash}",
                "num_faces": len(merged_faces),
                "faces": merged_faces
            }

            json_path = os.path.join(SAVE_DIR, f"{image_hash}.json")
            with open(json_path, "w") as f:
                json.dump(final_data, f, indent=2)

            logger.log_info(f"[STORAGE] Merged data for image {image_hash} saved to {json_path}")

            # Cleanup
            r.delete(f"merged:{image_hash}:landmarks")
            r.delete(f"merged:{image_hash}:agegender")

            return aggregator_pb2.FaceResultResponse(response=True)

        except Exception as e:
            logger.log_error(f"[STORAGE] Exception in SaveFaceAttributes: {e}")
            return aggregator_pb2.FaceResultResponse(response=False)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    aggregator_pb2_grpc.add_AggregatorServicer_to_server(AggregatorService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.log_info("[STORAGE] Storage Service running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

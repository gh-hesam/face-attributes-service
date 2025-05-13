import gradio as gr
import redis
import hashlib
import os
import time

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

def get_image_hash(image_bytes):
    return hashlib.md5(image_bytes).hexdigest()

def upload_image(image):
    import io
    from PIL import Image
    buf = io.BytesIO()
    image.save(buf, format='JPEG')
    image_bytes = buf.getvalue()

    image_hash = get_image_hash(image_bytes)

    # Store original image
    r.set(f"image:{image_hash}", image_bytes)
    r.set(f"image:result:{image_hash}", image_bytes)
    r.lpush("task:landmark", image_hash) 
    r.lpush("task:agegender", image_hash)

    print(f"resicved  key: {image_hash}")
    return f"sent for processing key: {image_hash}"

def main():
    with gr.Blocks() as demo:
        gr.Markdown("Face Attributes Aggregator System --- Input Service")
        image_input = gr.Image(type="pil")
        output_text = gr.Textbox(label="Status")

        image_input.upload(fn=upload_image, inputs=image_input, outputs=output_text)

    demo.launch()

if __name__ == "__main__":
    main()

# these service reads all images and corresponding JSON data for plot and show results in a gradio app 
import os
import json
import cv2
import gradio as gr

DATA_DIR = "./saved_data"

def load_all_pairs():
    files = sorted(os.listdir(DATA_DIR))
    json_files = [f for f in files if f.endswith(".json")]
    pairs = []
    for json_file in json_files:
        image_file = json_file.replace(".json", ".jpg")
        json_path = os.path.join(DATA_DIR, json_file)
        image_path = os.path.join(DATA_DIR, image_file)
        if os.path.exists(image_path):
            pairs.append((json_path, image_path))
    return pairs

pairs = load_all_pairs()

def draw_faces(index):
    if index >= len(pairs):
        return None, f"✅ Done! {index} images processed.", index

    json_path, image_path = pairs[index]

    image = cv2.imread(image_path)
    if image is None:
        return None, f"[!] Failed to load {image_path}", index

    with open(json_path, 'r') as f:
        data = json.load(f)

    for face in data.get("faces", []):
        box = face.get("box", {})
        x1, y1, x2, y2 = box.get("x1"), box.get("y1"), box.get("x2"), box.get("y2")

        # Draw bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Draw age/gender
        ag = face.get("agegender", {})
        label = f"{ag.get('gender', '')}, {ag.get('age', '')}"
        cv2.putText(image, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Draw landmarks
        for pt in face.get("landmarks", []):
            x, y = pt.get("x"), pt.get("y")
            cv2.circle(image, (x, y), 1, (0, 0, 255), -1)

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image_rgb, f"Image {index+1}/{len(pairs)}: {os.path.basename(image_path)}", index + 1

with gr.Blocks() as demo:
    gr.Markdown("##  Results Visualization")
    image_display = gr.Image(type="numpy", label="Annotated Image")
    label_display = gr.Textbox(label="Info")
    next_button = gr.Button("Next")
    counter = gr.State(0)

    next_button.click(fn=draw_faces, inputs=counter, outputs=[image_display, label_display, counter])

demo.launch()
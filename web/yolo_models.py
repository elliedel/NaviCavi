from flask import Blueprint
from . import db
import os
import cv2
import numpy as np
from PIL import Image
import tempfile
import sys
from pathlib import Path
from ultralytics import YOLO

yolo_models = Blueprint("yolo-models", __name__)

file_path = Path(__file__).resolve()
root_path = file_path.parent
if root_path not in sys.path:
    sys.path.append(str(root_path))
ROOT = root_path.relative_to(Path.cwd())

# ML Model config 
TYPE_SEGMENT = root_path / "models" / "ToothType.pt"
CARIES_SEGMENT = root_path / "models" / "is_last.pt"

# Load model
tooth_type_model = YOLO(TYPE_SEGMENT)
caries_model = YOLO(CARIES_SEGMENT)

@yolo_models.route("/analyze", methods=["POST"])
def process_image(image_path):

    image = Image.open(image_path)
    image = image.resize((640, 640))

    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    tooth_type_results = tooth_type_model(opencv_image)[0]

    annotated_image = opencv_image.copy()

    tooth_types = {}

    for box in tooth_type_results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        tooth_type = tooth_type_results.names[int(box.cls)]
        tooth_types[(x1, y1, x2, y2)] = tooth_type

    annotated_od_image_path = os.path.join(tempfile.gettempdir(), "annotated_od.jpg")
    cv2.imwrite(annotated_od_image_path, annotated_image)

    caries_results = caries_model(opencv_image)[0]

    caries_detected = False
    caries_info = []

    for box, segmentation_mask in zip(caries_results.boxes, caries_results.masks):
        caries_detected = True
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        mask = segmentation_mask.data.cpu().numpy()[0]
        mask = (mask * 255).astype(np.uint8)
        colored_mask = cv2.applyColorMap(mask, cv2.COLORMAP_JET)
        annotated_image = cv2.addWeighted(annotated_image, 0.7, colored_mask, 0.3, 0)

        tooth_type = "Unknown"
        for (tx1, ty1, tx2, ty2), t_type in tooth_types.items():
            if x1 >= tx1 and y1 >= ty1 and x2 <= tx2 and y2 <= ty2:
                tooth_type = t_type
                break

        caries_info.append(f"Caries on {tooth_type}")

        cv2.putText(
            annotated_image,
            f"Caries {box.conf[0]:.2f}",
            (x1, y2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (47, 210, 168),
            2,
        )

    annotated_is_image_path = os.path.join(tempfile.gettempdir(), "annotated_is.jpg")
    cv2.imwrite(annotated_is_image_path, annotated_image)

    raw_image_path = os.path.join(tempfile.gettempdir(), "raw.jpg")
    cv2.imwrite(raw_image_path, opencv_image)

    combined_image = np.hstack((opencv_image, annotated_image))
    combined_image_path = os.path.join(tempfile.gettempdir(), "combined.jpg")
    cv2.imwrite(combined_image_path, combined_image)
    print(caries_info)
    return (
        raw_image_path,
        annotated_is_image_path,
        caries_info,
    )
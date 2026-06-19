import os
import json
import cv2
import numpy as np
import paddle

# 1. Strict Low-Memory & Dynamic Garbage Collection Controls
paddle.set_flags({
    "FLAGS_fraction_of_cpu_memory_to_use": 0.15,
    "FLAGS_eager_delete_scope": True,
    "FLAGS_fast_eager_deletion_mode": True,
    "FLAGS_allocator_strategy": "naive_best_fit"
})

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR

app = FastAPI(title="Optimized Arabic ID OCR Engine")

# 2. Hyperparameter-tuned OCR Engine for better character recall
ocr = PaddleOCR(
    use_angle_cls=True, 
    lang='ar', 
    use_mp=False,
    total_process_num=1,
    det_db_thresh=0.25,        # Lower threshold to capture faint or thin text
    det_db_box_thresh=0.5,    # Discards random pixel noise background artifacts
    det_db_unclip_ratio=2.0   # Expands bounding boxes slightly to avoid clipping Arabic script edges
)

def preprocess_image(image_path):
    """
    Cleans background noise, boosts contrast, and sharpens text shapes
    to massively increase accuracy on small text like national IDs.
    """
    # Read in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return
        
    # Step A: Dynamic resize upscale if image resolution is small
    h, w = img.shape[:2]
    if w < 1000 or h < 1000:
        img = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
    # Step B: Contrast Limited Adaptive Histogram Equalization (CLAHE)
    # This neutralizes tricky background gradients, shadows, and watermarks
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(img)
    
    # Step C: Subtle sharpening matrix to crisp up cursive Arabic loops
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    
    # Overwrite temporary disk asset with high-contrast asset
    cv2.imwrite(image_path, sharpened)

@app.post("/api/extract-id-complete")
async def extract_id_complete(front_file: UploadFile, back_file: UploadFile):
    
    def run_ocr_on_file(uploaded_file: UploadFile):
        if not uploaded_file:
            return []
            
        temp_image_path = f"/tmp/{uploaded_file.filename}"
        
        try:
            # Save uploaded binary file to stream
            with open(temp_image_path, "wb") as buffer:
                buffer.write(uploaded_file.file.read())
                
            # Process image to make it highly legible for the model
            preprocess_image(temp_image_path)
                
            # Run inference execution
            raw_result = ocr.ocr(temp_image_path, cls=True)
            
            extracted_lines = []
            if raw_result and raw_result[0] is not None:
                lines = raw_result[0]
                
                # Step D: Spatial Sorting Engine
                # First sort text strings top-to-bottom (y-axis coordinate)
                # For blocks sharing a row, sort right-to-left (x-axis descending) to match Arabic script
                lines.sort(key=lambda box: (box[0][0][1], -box[0][0][0]))
                
                for line in lines:
                    extracted_lines.append({
                        "text": line[1][0],
                        "confidence": round(float(line[1][1]), 4),
                        "box": line[0]
                    })
            return extracted_lines
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR Runtime Error: {str(e)}")
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    # Sequential execution to bypass memory crashes
    front_data = run_ocr_on_file(front_file)
    back_data = run_ocr_on_file(back_file)
    
    processed_data = {
        "front_side": {
            "filename": front_file.filename,
            "extracted_text": [item["text"] for item in front_data],
            "structured_lines": front_data
        },
        "back_side": {
            "filename": back_file.filename,
            "extracted_text": [item["text"] for item in back_data],
            "structured_lines": back_data
        }
    }
    
    # Save the structured file inside /tmp
    output_txt_path = "/tmp/combined_id_output.txt"
    with open(output_txt_path, "w", encoding="utf-8") as txt_file:
        json.dump(processed_data, txt_file, ensure_ascii=False, indent=4)
        
    return JSONResponse(content={
        "status": "success",
        "saved_text_file": output_txt_path,
        "data": processed_data
    })

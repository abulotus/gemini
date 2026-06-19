import os
import json
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR

app = FastAPI(title="PaddleOCR Arabic API Pipeline")

# Optimized initialization to save memory on Railway
ocr = PaddleOCR(use_angle_cls=True, lang='ar', use_mp=False)

# 1. Update the route to match your exact URL path
@app.post("/api/extract-id-complete")
async def extract_id_complete(front_file: UploadFile, back_file: UploadFile):
    
    # Simple validation helper to run OCR on a single file
    def run_ocr_on_file(uploaded_file: UploadFile):
        if not uploaded_file:
            return []
            
        base_name, _ = os.path.splitext(uploaded_file.filename)
        temp_image_path = f"/tmp/{uploaded_file.filename}"
        
        try:
            # Save file to /tmp
            with open(temp_image_path, "wb") as buffer:
                buffer.write(uploaded_file.file.read())
                
            # Run PaddleOCR
            raw_result = ocr.ocr(temp_image_path, cls=True)
            
            extracted_lines = []
            if raw_result and raw_result[0] is not None:
                for line in raw_result[0]:
                    text_string = line[1][0]
                    confidence_score = float(line[1][1])
                    box_coordinates = line[0]
                    
                    extracted_lines.append({
                        "text": text_string,
                        "confidence": confidence_score,
                        "box": box_coordinates
                    })
            return extracted_lines
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing {uploaded_file.filename}: {str(e)}")
        finally:
            # Clean up image from disk instantly
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    # 2. Process both files sequentially
    front_data = run_ocr_on_file(front_file)
    back_data = run_ocr_on_file(back_file)
    
    # 3. Combine into the comprehensive structure
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
    
    # 4. Save the full JSON tracking payload to your /tmp folder
    output_txt_path = "/tmp/combined_id_output.txt"
    with open(output_txt_path, "w", encoding="utf-8") as txt_file:
        json.dump(processed_data, txt_file, ensure_ascii=False, indent=4)
        
    return JSONResponse(content={
        "status": "success",
        "saved_text_file": output_txt_path,
        "data": processed_data
    })

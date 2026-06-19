import os
import json
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR

# 1. Initialize FastAPI app
app = FastAPI(title="PaddleOCR Arabic API Pipeline")

# 2. Initialize PaddleOCR core engine (forces cache download on first API call)
# Using 'ar' for Arabic and enabling the direction/angle classifier
ocr = PaddleOCR(use_angle_cls=True, lang='ar', use_mp=False)

@app.post("/ocr")
async def process_ocr(file: UploadFile):
    # Validate that an actual file was uploaded
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    # Create filenames for temporary environment storage
    base_name, _ = os.path.splitext(file.filename)
    temp_image_path = f"/tmp/{file.filename}"
    output_txt_path = f"/tmp/{base_name}_output.txt"
    
    try:
        # Step 1: Write incoming stream data to a localized temp image file
        with open(temp_image_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Step 2: Run inference through PaddleOCR engine
        # result structure: [ [ [ [box coords], (text, confidence) ], ... ] ]
        raw_result = ocr.ocr(temp_image_path, cls=True)
        
        # Guard clause for empty/unreadable images
        if not raw_result or raw_result[0] is None:
            processed_data = {"filename": file.filename, "extracted_text": [], "structured_lines": []}
        else:
            # Step 3: Clean up raw arrays into clean structural mappings
            extracted_text_only = []
            structured_lines = []
            
            for line in raw_result[0]:
                box_coordinates = line[0]
                text_string = line[1][0]
                confidence_score = float(line[1][1]) # Cast float32 to native python float
                
                extracted_text_only.append(text_string)
                structured_lines.append({
                    "text": text_string,
                    "confidence": confidence_score,
                    "box": box_coordinates
                })
                
            processed_data = {
                "filename": file.filename,
                "extracted_text": extracted_text_only,
                "structured_lines": structured_lines
            }
            
        # Step 4: Serialize the processed data into beautiful JSON format 
        # and save it explicitly to a text file inside the /tmp folder
        with open(output_txt_path, "w", encoding="utf-8") as txt_file:
            json.dump(processed_data, txt_file, ensure_ascii=False, indent=4)
            
        # Step 5: Return JSONResponse alongside confirmation path pointers
        return JSONResponse(content={
            "status": "success",
            "saved_text_file": output_txt_path,
            "data": processed_data
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
        
    finally:
        # Clean up the incoming source image to maintain server disk space
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

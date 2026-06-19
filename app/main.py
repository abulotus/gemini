import os
import json

# --- ADD THESE FLAGS AT THE VERY TOP OF main.py (Before importing paddleocr) ---
import paddle
paddle.set_flags({
    "FLAGS_fraction_of_cpu_memory_to_use": 0.15,  # Limit memory footprint pool
    "FLAGS_eager_delete_scope": True,             # Clean temporary data instantly
    "FLAGS_fast_eager_deletion_mode": True,       # Fast garbage collection mode
    "FLAGS_allocator_strategy": "naive_best_fit"  # Avoid memory fragmentation
})
# ------------------------------------------------------------------------------

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR

app = FastAPI(title="PaddleOCR Arabic API Pipeline")

# Limit internal execution threads to prevent CPU/RAM overhead thrashing
ocr = PaddleOCR(
    use_angle_cls=True, 
    lang='ar', 
    use_mp=False,      # Disables multiprocessing overhead
    total_process_num=1 # Forces sequential execution architecture
)

@app.post("/api/extract-id-complete")
async def extract_id_complete(front_file: UploadFile, back_file: UploadFile):
    
    def run_ocr_on_file(uploaded_file: UploadFile):
        if not uploaded_file:
            return []
            
        temp_image_path = f"/tmp/{uploaded_file.filename}"
        
        try:
            with open(temp_image_path, "wb") as buffer:
                buffer.write(uploaded_file.file.read())
                
            raw_result = ocr.ocr(temp_image_path, cls=True)
            
            extracted_lines = []
            if raw_result and raw_result[0] is not None:
                for line in raw_result[0]:
                    extracted_lines.append({
                        "text": line[1][0],
                        "confidence": float(line[1][1]),
                        "box": line[0]
                    })
            return extracted_lines
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    # Process the files sequentially to prevent concurrent memory spikes
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
    
    output_txt_path = "/tmp/combined_id_output.txt"
    with open(output_txt_path, "w", encoding="utf-8") as txt_file:
        json.dump(processed_data, txt_file, ensure_ascii=False, indent=4)
        
    return JSONResponse(content={
        "status": "success",
        "saved_text_file": output_txt_path,
        "data": processed_data
    })

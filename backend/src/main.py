from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import zxing
from PIL import Image
import io

app = FastAPI(title="Barcode Decoder API")

# 1. Define specific origins for CORS security compatibility
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://bar-front-production.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Crucial: Specify domains instead of "*" when allow_credentials=True
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

JAVA_PATH = "/usr/bin/java"
if not os.path.exists(JAVA_PATH):
    reader = zxing.BarCodeReader()
else:
    reader = zxing.BarCodeReader(java=JAVA_PATH)

@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Bar code processor is ready!"}

@app.post("/decode-barcode")
@app.post("/decode-barcode")
async def decode_barcode(file: UploadFile = File(...)):
    print("\n--- 🚨 NEW DECODE ATTEMPT START 🚨 ---")
    print(f"Content Type Received: {file.content_type}")
    
    # Define a permanent debug path inside your container
    debug_dir = "/app/debug_uploads"
    os.makedirs(debug_dir, exist_ok=True)
    saved_photo_path = os.path.join(debug_dir, "last_uploaded_id.png")
    json_log_path = os.path.join(debug_dir, "last_decode_result.json")

    try:
        # Read the file raw bytes
        image_bytes = await file.read()
        print(f"Bytes read successfully: {len(image_bytes)} bytes")
        
        # Save the exact image to disk immediately for server inspection
        with open(saved_photo_path, "wb") as f:
            f.write(image_bytes)
        print(f"📁 SUCCESS: Raw image saved to server disk at: {saved_photo_path}")

        # Attempt to open with Pillow
        try:
            image = Image.open(io.BytesIO(image_bytes))
            print(f"📸 Pillow parsed image format: {image.format}, size: {image.size}, mode: {image.mode}")
            
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
                # Save the cropped/converted version too
                width, height = image.size
                image = image.crop((0, int(height * 0.60), width, height))
                image.save(os.path.join(debug_dir, "last_cropped_processed.png"))
                print("✂️ Cropped image saved successfully.")
        except Exception as img_err:
            print(f"❌ PILLOW FAILURE: {str(img_err)}")
            raise HTTPException(status_code=422, detail=f"Pillow crash: {str(img_err)}")

        # Send to ZXing
        print("🔍 Invoking ZXing via Java...")
        barcode = reader.decode(saved_photo_path)
        
        # Structure the payload
        response_data = {"success": False, "message": "No barcode parsed by ZXing."}
        
        if barcode and barcode.parsed:
            raw_data = barcode.parsed
            print(f"🎉 ZXing parsed string: {raw_data[:30]}...")
            
            try:
                fixed_data = raw_data.encode('iso-8859-1').decode('windows-1256')
            except Exception:
                fixed_data = raw_data

            parts = fixed_data.split('#')
            useful_profile = {}
            if len(parts) >= 6:
                useful_profile = {
                    "first_name": parts[0], "last_name": parts[1],
                    "father_name": parts[2], "mother_name": parts[3],
                    "birth_place_and_date": parts[4], "national_number": parts[5]
                }

            response_data = {
                "success": True,
                "format": barcode.format,
                "profile": useful_profile,
                "raw_payload": fixed_data
            }
        
        # Write JSON payload onto server disk
        import json
        with open(json_log_path, "w", encoding="utf-8") as json_file:
            json.dump(response_data, json_file, indent=4, ensure_ascii=False)
        print(f"💾 SUCCESS: JSON result saved to server disk at: {json_log_path}")

        return response_data

    except Exception as e:
        error_msg = {"success": False, "error": f"Critical API crash: {str(e)}"}
        print(f"🚨 CRITICAL API CRASH: {str(e)}")
        with open(json_log_path, "w") as json_file:
            json.dump(error_msg, json_file)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

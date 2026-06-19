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
    allow_credentials=True,
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
async def decode_barcode(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        print(f"❌ REJECTED: Invalid content type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File provided is not an image.")
    
    try:
        image_bytes = await file.read()
        print(f"📸 Image received. Size: {len(image_bytes)} bytes")
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as img_err:
            print(f"❌ PILLOW CRASH: Failed to parse image bytes: {str(img_err)}")
            raise HTTPException(status_code=422, detail="Invalid or corrupt image format.")

        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Crop the image to target the barcode on the back of a card
        width, height = image.size
        left = 0
        top = int(height * 0.60)
        right = width
        bottom = height
        cropped_image = image.crop((left, top, right, bottom))

        temp_filename = "temp_crop.png"
        cropped_image.save(temp_filename)
        print("🔍 Saved cropped image. Sending to ZXing...")

        try:
            barcode = reader.decode(temp_filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ZXing internal error: {str(e)}")
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        if barcode and barcode.parsed:
            raw_data = barcode.parsed
            print(f"✅ ZXing successfully parsed barcode raw data")
            
            try:
                fixed_data = raw_data.encode('iso-8859-1').decode('windows-1256')
            except Exception:
                try:
                    fixed_data = raw_data.encode('iso-8859-1').decode('iso-8859-6')
                except Exception:
                    fixed_data = raw_data

            parts = fixed_data.split('#')
            useful_profile = {}
            
            if len(parts) >= 6:
                useful_profile = {
                    "first_name": parts[0],
                    "last_name": parts[1],
                    "father_name": parts[2],
                    "mother_name": parts[3],
                    "birth_place_and_date": parts[4],
                    "national_number": parts[5]
                }
                
                try:
                    birth_info = parts[4].split(' ')
                    useful_profile["birth_place"] = birth_info[0]
                    useful_profile["birth_date"] = birth_info[1]
                except Exception:
                    pass

            return {
                "success": True,
                "format": barcode.format,
                "profile": useful_profile,
                "raw_payload": fixed_data
            }
        else:
            return {
                "success": False,
                "message": "No barcode detected or could not be cleanly decoded."
            }
            
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"🚨 CRITICAL BACKEND ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

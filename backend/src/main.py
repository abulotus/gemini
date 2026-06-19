from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import zxing
from PIL import Image
import io

# ONLY ONE INSTANCE OF APP REQUIRED
app = FastAPI(title="Barcode Decoder API")

# Define the origins allowed to talk to your backend
origins = [
    "http://localhost:5173",    
    "http://127.0.0.1:5173",  
    "https://bar-front-production.up.railway.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           
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
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file format.")

    # Crop the image to target the barcode on the back of a card
    width, height = image.size
    left = 0
    top = int(height * 0.60)
    right = width
    bottom = height
    cropped_image = image.crop((left, top, right, bottom))

    # Save to a safe absolute path inside the /code working directory
    temp_filename = "/code/temp_crop.png"
    cropped_image.save(temp_filename)

    try:
        barcode = reader.decode(temp_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZXing internal error: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    if barcode and barcode.parsed:
        raw_data = barcode.parsed
        
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
            "message": "Barcode found, but could not be cleanly decoded."
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

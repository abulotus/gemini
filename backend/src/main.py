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

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Try full image scan first
    temp_filename = "/code/temp_full.png"
    image.save(temp_filename)
    try:
        barcode = reader.decode(temp_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ZXing execution failure: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    # Fallback to bottom 60% crop if full image yields nothing
    if not barcode or not (barcode.parsed or barcode.raw):
        print("⚠️ Full scan empty. Running crop fallback...")
        width, height = image.size
        cropped_image = image.crop((0, int(height * 0.60), width, height))
        
        temp_crop_filename = "/code/temp_crop.png"
        cropped_image.save(temp_crop_filename)
        try:
            barcode = reader.decode(temp_crop_filename)
        finally:
            if os.path.exists(temp_crop_filename):
                os.remove(temp_crop_filename)

    # --- ENHANCED RETURN ENGINE ---
    if barcode:
        # Step 1: Capture whatever raw string engine grabbed
        raw_text = barcode.parsed if barcode.parsed else barcode.raw
        
        if not raw_text:
            return {
                "success": False,
                "message": f"Barcode layout found ({barcode.format}), but no internal text data stream was extracted."
            }

        # Step 2: Extract Arabic text encodings safely
        fixed_arabic_text = ""
        try:
            fixed_arabic_text = raw_text.encode('iso-8859-1').decode('windows-1256')
        except Exception:
            try:
                fixed_arabic_text = raw_text.encode('iso-8859-1').decode('iso-8859-6')
            except Exception:
                fixed_arabic_text = raw_text # Fallback to original text if both fail

        # Step 3: Split elements dynamically without strict limits
        parts = fixed_arabic_text.split('#')
        
        # Build out a profile structure map safely from whatever parts exist
        useful_profile = {
            "first_name": parts[0] if len(parts) > 0 else None,
            "last_name": parts[1] if len(parts) > 1 else None,
            "father_name": parts[2] if len(parts) > 2 else None,
            "mother_name": parts[3] if len(parts) > 3 else None,
            "birth_place_and_date": parts[4] if len(parts) > 4 else None,
            "national_number": parts[5] if len(parts) > 5 else None,
        }

        # Try to break out place and date if field 4 was extracted
        if useful_profile["birth_place_and_date"]:
            try:
                birth_info = useful_profile["birth_place_and_date"].split(' ')
                useful_profile["birth_place"] = birth_info[0]
                useful_profile["birth_date"] = birth_info[1]
            except Exception:
                pass

        # Return everything to your React app right away
        return {
            "success": True,
            "format": barcode.format,
            "raw_text_from_scanner": raw_text,       # Original unchanged scanner text
            "decoded_arabic_text": fixed_arabic_text, # Re-mapped Arabic string text
            "all_split_segments": parts,               # Raw list array of all elements split by '#'
            "profile": useful_profile                  # Key-value dictionary object map
        }
    else:
        return {
            "success": False,
            "message": "No barcode configuration or patterns could be recognized in this image file."
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

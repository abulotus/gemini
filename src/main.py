from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import os
import zxing
from PIL import Image
import io

app = FastAPI()

# Point to the absolute path of the Java binary in the container
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
    # 1. Read the uploaded image file bytes
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file format.")

    # 2. Crop the image to target the barcode on the back of a card
    width, height = image.size
    left = 0
    top = int(height * 0.60)
    right = width
    bottom = height
    cropped_image = image.crop((left, top, right, bottom))

    # 3. Save the cropped image temporarily for ZXing to read
    temp_filename = "temp_crop.png"
    cropped_image.save(temp_filename)

    # 4. Use ZXing to decode the barcode
    try:
        barcode = reader.decode(temp_filename)
    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=f"ZXing internal error: {str(e)}")

    # Clean up the temporary cropped image
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    # 5. Process results and save to text file with Arabic encoding (utf-8)
    if barcode and barcode.parsed:
        raw_data = barcode.parsed
        
        # MOJIBAKE FIX: Convert garbled Latin-1 characters back to raw bytes, 
        # then cleanly decode them into Arabic.
        try:
            # Windows-1256 is the most common encoding for Middle Eastern IDs/cards
            fixed_data = raw_data.encode('iso-8859-1').decode('windows-1256')
        except Exception:
            try:
                # Fallback to standard ISO Arabic encoding if Windows-1256 fails
                fixed_data = raw_data.encode('iso-8859-1').decode('iso-8859-6')
            except Exception:
                # Final fallback: keep original if everything else fails
                fixed_data = raw_data

        # 6. Structured Data Extraction
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
            
            # Sub-split the place and date of birth if space-separated
            try:
                birth_info = parts[4].split(' ')
                useful_profile["birth_place"] = birth_info[0]
                useful_profile["birth_date"] = birth_info[1]
            except Exception:
                pass

        # 7. Write Structured Data & Payloads into text file
        output_txt_file = "barcode_result.txt"
        with open(output_txt_file, "w", encoding="utf-8") as f:
            f.write("=== BARCODE DECODING RESULT ===\n")
            f.write(f"Format: {barcode.format}\n\n")
            
            f.write("--- EXTRACTED PARSED PROFILE ---\n")
            for key, val in useful_profile.items():
                f.write(f"{key}: {val}\n")
            f.write("\n")
            
            f.write("--- FULL STRINGS ---\n")
            f.write(f"Fixed Arabic Data: {fixed_data}\n")
            f.write(f"Original Raw Payload: {raw_data}\n")
            
        return {
            "success": True,
            "message": f"Barcode successfully decoded, structured, and saved to server storage as {output_txt_file}",
            "profile_preview": useful_profile
        }

    else:
        return {
            "success": False,
            "message": "Barcode found, but could not be cleanly decoded."
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

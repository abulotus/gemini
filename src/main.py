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
        output_txt_file = "barcode_result.txt"
        
        # Open with encoding="utf-8" to seamlessly support Arabic script text
        with open(output_txt_file, "w", encoding="utf-8") as f:
            f.write(f"=== BARCODE DECODING RESULT ===\n")
            f.write(f"Format: {barcode.format}\n")
            f.write(f"Data: {barcode.parsed}\n")
            
        # Terminal/Curl client receives a confirmation instead of the long payload
        return {
            "success": True,
            "message": f"Barcode successfully decoded and saved to server storage as {output_txt_file}"
        }
    else:
        return {
            "success": False,
            "message": "Barcode found, but could not be cleanly decoded."
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

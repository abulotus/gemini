from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn
import os
import zxing
from PIL import Image
import io

app = FastAPI()

# Initialize the ZXing reader (it looks for Java automatically)
reader = zxing.BarCodeReader()

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
    # (Left, Top, Right, Bottom) coordinate bounding box
    width, height = image.size
    
    # Example: Cropping the bottom 40% of the card where a barcode usually sits
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
        # Clean up file if zxing crashes internally
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=f"ZXing internal error: {str(e)}")

    # Clean up the temporary file
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

    # 5. Return the result
    if barcode and barcode.parsed:
        return {
            "success": True,
            "format": barcode.format,
            "data": barcode.parsed
        }
    else:
        return {
            "success": False,
            "message": "Barcode found, but could not be cleanly decoded or cropped region missed it."
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

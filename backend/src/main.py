from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import zxing
from PIL import Image
import io
import tempfile

app = FastAPI(title="Barcode Decoder API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://bar-front-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JAVA_PATH = "/usr/bin/java"

if os.path.exists(JAVA_PATH):
    reader = zxing.BarCodeReader(java=JAVA_PATH)
else:
    reader = zxing.BarCodeReader()


def decode_image_with_tempfile(image: Image.Image):
    temp_filename = None

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_filename = tmp.name
            image.save(temp_filename)

        return reader.decode(temp_filename)

    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "message": "Barcode processor is ready!",
    }


@app.post("/decode-barcode")
async def decode_barcode(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File provided is not an image.",
        )

    contents = await file.read()

    try:
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file format.",
        )

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    try:
        barcode = decode_image_with_tempfile(image)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ZXing execution failure: {str(e)}",
        )

    if not barcode or not (barcode.parsed or barcode.raw):
        width, height = image.size
        cropped_image = image.crop((0, int(height * 0.60), width, height))

        try:
            barcode = decode_image_with_tempfile(cropped_image)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"ZXing crop execution failure: {str(e)}",
            )

    if not barcode:
        return {
            "success": False,
            "message": "No barcode configuration or patterns could be recognized in this image file.",
        }

    raw_text = barcode.parsed if barcode.parsed else barcode.raw

    if not raw_text:
        return {
            "success": False,
            "message": f"Barcode layout found ({barcode.format}), but no internal text data stream was extracted.",
        }

    try:
        fixed_arabic_text = raw_text.encode("iso-8859-1").decode("windows-1256")
    except Exception:
        try:
            fixed_arabic_text = raw_text.encode("iso-8859-1").decode("iso-8859-6")
        except Exception:
            fixed_arabic_text = raw_text

    parts = fixed_arabic_text.split("#")

    profile = {
        "first_name": parts[0] if len(parts) > 0 else None,
        "last_name": parts[1] if len(parts) > 1 else None,
        "father_name": parts[2] if len(parts) > 2 else None,
        "mother_name": parts[3] if len(parts) > 3 else None,
        "birth_place_and_date": parts[4] if len(parts) > 4 else None,
        "national_number": parts[5] if len(parts) > 5 else None,
    }

    if profile["birth_place_and_date"]:
        birth_info = profile["birth_place_and_date"].split(" ")

        if len(birth_info) >= 2:
            profile["birth_place"] = birth_info[0]
            profile["birth_date"] = birth_info[1]
        else:
            profile["birth_place"] = profile["birth_place_and_date"]
            profile["birth_date"] = None

    return {
        "success": True,
        "format": barcode.format,
        "raw_text_from_scanner": raw_text,
        "decoded_arabic_text": fixed_arabic_text,
        "all_split_segments": parts,
        "profile": profile,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
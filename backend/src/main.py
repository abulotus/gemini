from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import os
import io
import tempfile

import zxing
import cv2
import numpy as np
from PIL import Image


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
        if image.mode != "RGB":
            image = image.convert("RGB")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temp_filename = tmp.name
            image.save(temp_filename, format="JPEG", quality=98)

        return reader.decode(temp_filename)

    finally:
        if temp_filename and os.path.exists(temp_filename):
            os.remove(temp_filename)


def generate_image_variants(image: Image.Image):
    if image.mode != "RGB":
        image = image.convert("RGB")

    image_np = np.array(image)
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    variants = []

    variants.append(("original", image))
    variants.append(("gray", Image.fromarray(gray)))

    upscaled = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC,
    )
    variants.append(("upscaled_gray", Image.fromarray(upscaled)))

    blur = cv2.GaussianBlur(upscaled, (0, 0), 3)
    sharp = cv2.addWeighted(upscaled, 1.8, blur, -0.8, 0)
    variants.append(("sharp", Image.fromarray(sharp)))

    threshold = cv2.adaptiveThreshold(
        sharp,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        5,
    )
    variants.append(("threshold", Image.fromarray(threshold)))

    return variants


def try_decode_variants(image: Image.Image):
    variants = generate_image_variants(image)

    for method, variant in variants:
        try:
            barcode = decode_image_with_tempfile(variant)

            if barcode and (barcode.parsed or barcode.raw):
                return barcode, method

        except Exception:
            continue

    return None, None


def decode_arabic_text(raw_text: str):
    try:
        return raw_text.encode("iso-8859-1").decode("windows-1256")
    except Exception:
        try:
            return raw_text.encode("iso-8859-1").decode("iso-8859-6")
        except Exception:
            return raw_text


def parse_profile(fixed_arabic_text: str):
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
        birth_info = profile["birth_place_and_date"].rsplit("  ", 1)

        if len(birth_info) >= 2:
            profile["birth_place"] = birth_info[0]
            profile["birth_date"] = birth_info[1]
        else:
            profile["birth_place"] = profile["birth_place_and_date"]
            profile["birth_date"] = None

    return parts, profile


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
        image.load()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file format.",
        )

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    decode_method = None

    try:
        barcode, decode_method = try_decode_variants(image)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ZXing execution failure: {str(e)}",
        )

    if not barcode or not (barcode.parsed or barcode.raw):
        width, height = image.size

        crop_regions = [
            ("bottom_50", image.crop((0, int(height * 0.50), width, height))),
            ("bottom_40", image.crop((0, int(height * 0.60), width, height))),
            (
                "middle_lower",
                image.crop((0, int(height * 0.45), width, int(height * 0.88))),
            ),
            (
                "center",
                image.crop((0, int(height * 0.25), width, int(height * 0.75))),
            ),
        ]

        for crop_name, cropped_image in crop_regions:
            barcode, method = try_decode_variants(cropped_image)

            if barcode and (barcode.parsed or barcode.raw):
                decode_method = f"{crop_name}_{method}"
                break

    if not barcode:
        return {
            "success": False,
            "message": "No barcode configuration or patterns could be recognized in this image file.",
            "decode_method": decode_method,
        }

    raw_text = barcode.parsed if barcode.parsed else barcode.raw

    if not raw_text:
        return {
            "success": False,
            "message": f"Barcode layout found ({barcode.format}), but no internal text data stream was extracted.",
            "decode_method": decode_method,
        }

    fixed_arabic_text = decode_arabic_text(raw_text)
    parts, profile = parse_profile(fixed_arabic_text)

    return {
        "success": True,
        "format": barcode.format,
        "decode_method": decode_method,
        "raw_text_from_scanner": raw_text,
        "decoded_arabic_text": fixed_arabic_text,
        "all_split_segments": parts,
        "profile": profile,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
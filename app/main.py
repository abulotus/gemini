from fastapi import FastAPI, UploadFile, File, HTTPException
import cv2
import numpy as np
import pytesseract
import zxing
import re
import os

app = FastAPI()
reader = zxing.BarCodeReader()

def extract_text_from_image(image_bytes: bytes) -> str:
    """Pre-processes the image and extracts text using Tesseract OCR."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image file.")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    custom_config = r'--oem 3 --psm 6 -l ara'
    return pytesseract.image_to_string(resized, config=custom_config)

def parse_front_side(text: str) -> dict:
    """Parses text fields from the front of the card."""
    name = re.search(r'الاسم[:\s]*(.+)', text)
    surname = re.search(r'النسبة[:\s]*(.+)', text)
    father = re.search(r'اسم الأب[:\s]*(.+)', text)
    mother = re.search(r'اسم و نسبة الأم[:\s]*(.+)', text)
    dob = re.search(r'محل و تاريخ الولادة[:\s]*(.+)', text)
    national_id = re.search(r'الرقم الوطني[:\s]*([\d\-\s]+)', text)

    clean = lambda m: m.group(1).strip().replace('\n', ' ') if m else "Not Found"
    return {
        "first_name": clean(name),
        "surname": clean(surname),
        "father_name": clean(father),
        "mother_info": clean(mother),
        "place_and_date_of_birth": clean(dob),
        "national_number": clean(national_id).replace(" ", "")
    }

def parse_back_side(text: str) -> dict:
    """Parses text fields from the back of the card."""
    registry = re.search(r'الأمانة[:\s]*(.+)', text)
    record = re.search(r'القيد[:\s]*(.+)', text)
    gender = re.search(r'الجنس[:\s]*(.+)', text)
    address = re.search(r'العنوان[:\s]*(.+)', text)
    issue_date = re.search(r'تاريخ المنح[:\s]*(.+)', text)

    clean = lambda m: m.group(1).strip().replace('\n', ' ') if m else "Not Found"
    return {
        "civil_registry": clean(registry),
        "record_number": clean(record),
        "gender": clean(gender),
        "address": clean(address),
        "issue_date": clean(issue_date)
    }

def decode_barcode(image_bytes: bytes) -> str:
    """Crops the bottom area and parses the PDF417 barcode using ZXing."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return "Failed to process image for barcode"

    h, w, _ = img.shape
    barcode_region = img[int(h * 0.6):h, 0:w]
    
    temp_filename = "temp_barcode_proc.png"
    cv2.imwrite(temp_filename, barcode_region)
    
    try:
        barcode = reader.decode(temp_filename)
        return barcode.parsed if barcode and barcode.parsed else "Not Readable"
    except Exception:
        return "Not Readable"
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.post("/api/extract-id-complete")
async def extract_full_id(
    front_file: UploadFile = File(...), 
    back_file: UploadFile = File(...)
):
    valid_types = ["image/jpeg", "image/png"]
    if front_file.content_type not in valid_types or back_file.content_type not in valid_types:
        raise HTTPException(status_code=400, detail="Both files must be JPEG or PNG images.")
    
    try:
        # Read file uploads
        front_bytes = await front_file.read()
        back_bytes = await back_file.read()
        
        # Run extractions
        front_text = extract_text_from_image(front_bytes)
        back_text = extract_text_from_image(back_bytes)
        barcode_data = decode_barcode(back_bytes)
        
        # Structure the payload
        return {
            "status": "success",
            "extracted_data": {
                "front_side": parse_front_side(front_text),
                "back_side": parse_back_side(back_text),
                "barcode_raw_payload": barcode_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing pipeline failed: {str(e)}")

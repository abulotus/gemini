from fastapi import FastAPI, UploadFile, File, HTTPException
import cv2
import numpy as np
import pytesseract
import zxing
import re
import os

app = FastAPI()
reader = zxing.BarCodeReader()

def clean_and_threshold_image(image_bytes: bytes):
    """Cleans up phone shadows and sharpens text for OCR."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image file.")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Use Adaptive Thresholding to handle uneven lighting/shadows from phone cameras
    processed = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Upscale slightly to make small ID text easier to read
    resized = cv2.resize(processed, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    return resized

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text using Tesseract with Arabic settings."""
    processed_img = clean_and_threshold_image(image_bytes)
    custom_config = r'--oem 3 --psm 4 -l ara' # PSM 4 assumes a single column of text with varying sizes
    return pytesseract.image_to_string(processed_img, config=custom_config)

def parse_front_side(text: str) -> dict:
    """More forgiving parser looking for Arabic keywords anywhere on a line."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    res = {
        "first_name": "Not Found", "surname": "Not Found", "father_name": "Not Found",
        "mother_info": "Not Found", "place_and_date_of_birth": "Not Found", "national_number": "Not Found"
    }
    
    for line in lines:
        # Look for keywords dynamically anywhere in the read line
        if "الاسم" in line:
            res["first_name"] = line.replace("الاسم", "").strip(" :--_")
        elif "النسبة" in line or "العائلة" in line:
            res["surname"] = line.replace("النسبة", "").strip(" :--_")
        elif "الأب" in line or "الاب" in line:
            res["father_name"] = line.replace("اسم الأب", "").replace("الأب", "").strip(" :--_")
        elif "الأم" in line or "الام" in line:
            res["mother_info"] = line.replace("اسم و نسبة الأم", "").replace("الأم", "").strip(" :--_")
        elif "الولادة" in line:
            res["place_and_date_of_birth"] = line.replace("محل و تاريخ الولادة", "").replace("الولادة", "").strip(" :--_")
            
    # National number lookup: hunt for any standalone sequence of 11 digits
    digits_match = re.search(r'\b\d{11}\b', text.replace(" ", "").replace("‌", ""))
    if digits_match:
        res["national_number"] = digits_match.group(0)
        
    return res

def parse_back_side(text: str) -> dict:
    """More forgiving parser for the back details."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    res = {
        "civil_registry": "Not Found", "record_number": "Not Found", 
        "gender": "Not Found", "address": "Not Found", "issue_date": "Not Found"
    }
    
    for line in lines:
        if "الأمانة" in line or "الامانة" in line:
            res["civil_registry"] = line.replace("الأمانة", "").strip(" :--_")
        elif "القيد" in line:
            res["record_number"] = line.replace("القيد", "").strip(" :--_")
        elif "الجنس" in line:
            res["gender"] = line.replace("الجنس", "").strip(" :--_")
        elif "العنوان" in line:
            res["address"] = line.replace("العنوان", "").strip(" :--_")
        elif "المنح" in line:
            res["issue_date"] = line.replace("تاريخ المنح", "").strip(" :--_")
            
    return res

def decode_barcode(image_bytes: bytes) -> str:
    """Attempts to decode the PDF417 barcode directly from the whole back image or cropped area."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return "Not Readable"

    temp_filename = "temp_barcode_proc.png"
    
    # Try decoding the full image first, then try a crop if it fails
    cv2.imwrite(temp_filename, img)
    barcode = reader.decode(temp_filename)
    
    if not (barcode and barcode.parsed):
        # Crop lower 40% if the first pass fails
        h, w, _ = img.shape
        barcode_region = img[int(h * 0.6):h, 0:w]
        cv2.imwrite(temp_filename, barcode_region)
        barcode = reader.decode(temp_filename)
        
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    return barcode.parsed if barcode and barcode.parsed else "Not Readable"

@app.post("/api/extract-id-complete")
async def extract_full_id(front_file: UploadFile, back_file: UploadFile):
    try:
        front_bytes = await front_file.read()
        back_bytes = await back_file.read()
        
        front_text = extract_text_from_image(front_bytes)
        back_text = extract_text_from_image(back_bytes)
        barcode_data = decode_barcode(back_bytes)
        
        return {
            "status": "success",
            "extracted_data": {
                "front_side": parse_front_side(front_text),
                "back_side": parse_back_side(back_text),
                "barcode_raw_payload": barcode_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

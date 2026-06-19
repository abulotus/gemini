from fastapi import FastAPI, UploadFile, HTTPException
import cv2
import numpy as np
import zxing
import os
from paddleocr import PaddleOCR

app = FastAPI()
reader = zxing.BarCodeReader()

# Initialize PaddleOCR with Arabic language support ('ar')
# use_angle_cls=True automatically handles rotated/upside-down text lines!
ocr = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)

def extract_text_lines(image_bytes: bytes) -> list:
    """Passes image to PaddleOCR and returns a flat list of detected text strings."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image file.")
        
    # PaddleOCR handles resizing and normalization internally
    result = ocr.ocr(img, cls=True)
    
    lines = []
    if result and result[0]:
        for line in result[0]:
            text_val = line[1][0]  # Extract text string component
            lines.append(text_val.strip())
    return lines

def parse_front_side(lines: list) -> dict:
    res = {
        "first_name": "Not Found", "surname": "Not Found", "father_name": "Not Found",
        "mother_info": "Not Found", "place_and_date_of_birth": "Not Found", "national_number": "Not Found"
    }
    
    # Iterate through lines to find corresponding values
    for i, line in enumerate(lines):
        if "الاسم" in line:
            # If the value is in the same text box line, clean it. Otherwise, check next box line.
            res["first_name"] = line.replace("الاسم", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "النسبة" in line or "العائلة" in line:
            res["surname"] = line.replace("النسبة", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الأب" in line or "الاب" in line:
            res["father_name"] = line.replace("اسم الأب", "").replace("الأب", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الأم" in line or "الام" in line:
            res["mother_info"] = line.replace("اسم و نسبة الأم", "").replace("الأم", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الولادة" in line:
            res["place_and_date_of_birth"] = line.replace("محل و تاريخ الولادة", "").replace("الولادة", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
            
        # Extract 11 digit national ID numbers
        digits = "".join(filter(str.isdigit, line))
        if len(digits) == 11:
            res["national_number"] = digits
            
    return res

def parse_back_side(lines: list) -> dict:
    res = {
        "civil_registry": "Not Found", "record_number": "Not Found", 
        "gender": "Not Found", "address": "Not Found", "issue_date": "Not Found"
    }
    
    for i, line in enumerate(lines):
        if "الأمانة" in line or "الامانة" in line:
            res["civil_registry"] = line.replace("الأمانة", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "القيد" in line:
            res["record_number"] = line.replace("القيد", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الجنس" in line:
            res["gender"] = line.replace("الجنس", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "العنوان" in line:
            res["address"] = line.replace("العنوان", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "المنح" in line:
            res["issue_date"] = line.replace("تاريخ المنح", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
            
    return res

def decode_barcode(image_bytes: bytes) -> str:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return "Not Readable"

    temp_filename = "temp_barcode_proc.png"
    cv2.imwrite(temp_filename, img)
    barcode = reader.decode(temp_filename)
    
    if not (barcode and barcode.parsed):
        h, w, _ = img.shape
        barcode_region = img[int(h * 0.5):h, 0:w] # Try lower half
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
        
        front_lines = extract_text_lines(front_bytes)
        back_lines = extract_text_lines(back_bytes)
        barcode_data = decode_barcode(back_bytes)
        
        return {
            "status": "success",
            "extracted_data": {
                "front_side": parse_front_side(front_lines),
                "back_side": parse_back_side(back_lines),
                "barcode_raw_payload": barcode_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

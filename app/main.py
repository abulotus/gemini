from fastapi import FastAPI, UploadFile, HTTPException
import cv2
import numpy as np
import zxing
import os
from paddleocr import PaddleOCR

app = FastAPI()
reader = zxing.BarCodeReader()
ocr = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)

def fix_arabic_encoding(raw_str: str) -> str:
    """Fixes Mojibake by casting Latin-1 mis-read strings back to Arabic Windows-1256."""
    try:
        # Convert back to raw bytes using the incorrect encoding, then read as Arabic
        return raw_str.encode('latin1').decode('windows-1256')
    except Exception:
        return raw_str # Return original if conversion fails

def extract_text_lines(image_bytes: bytes) -> list:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []
    result = ocr.ocr(img, cls=True)
    lines = []
    if result and result[0]:
        for line in result[0]:
            lines.append(line[1][0].strip())
    return lines

def parse_front_side(lines: list) -> dict:
    res = {
        "first_name": "Not Found", "surname": "Not Found", "father_name": "Not Found",
        "mother_info": "Not Found", "place_and_date_of_birth": "Not Found", "national_number": "Not Found"
    }
    for i, line in enumerate(lines):
        if "الاسم" in line:
            res["first_name"] = line.replace("الاسم", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "النسبة" in line or "العائلة" in line:
            res["surname"] = line.replace("النسبة", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الأب" in line or "الاب" in line:
            res["father_name"] = line.replace("الأب", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الأم" in line or "الام" in line:
            res["mother_info"] = line.replace("الأم", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        elif "الولادة" in line:
            res["place_and_date_of_birth"] = line.replace("الولادة", "").strip(" :--_") or (lines[i+1] if i+1 < len(lines) else "Not Found")
        
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
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return "Not Readable"

    temp_filename = "temp_barcode_proc.png"
    cv2.imwrite(temp_filename, img)
    barcode = reader.decode(temp_filename)
    
    if not (barcode and barcode.parsed):
        h, w, _ = img.shape
        barcode_region = img[int(h * 0.5):h, 0:w]
        cv2.imwrite(temp_filename, barcode_region)
        barcode = reader.decode(temp_filename)
        
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    if barcode and barcode.parsed:
        return fix_arabic_encoding(barcode.parsed)
    return "Not Readable"

@app.post("/api/extract-id-complete")
async def extract_full_id(front_file: UploadFile, back_file: UploadFile):
    try:
        front_bytes = await front_file.read()
        back_bytes = await back_file.read()
        
        # 1. Decode Barcode first (safest and most accurate data pool)
        decoded_barcode_str = decode_barcode(back_bytes)
        
        # 2. Run fallback OCR extraction
        front_lines = extract_text_lines(front_bytes)
        back_lines = extract_text_lines(back_bytes)
        
        front_data = parse_front_side(front_lines)
        back_data = parse_back_side(back_lines)
        
        # 3. Smart Fallback: If barcode read successfully, parse it to fill empty OCR slots
        if decoded_barcode_str and "#" in decoded_barcode_str:
            parts = decoded_barcode_str.split('#')
            # Typical Syrian ID barcode segments: Card Holder Name # Father Name # Mother Name # Birth Info # National Num
            if len(parts) >= 6:
                if front_data["first_name"] == "Not Found": 
                    front_data["first_name"] = parts[0]
                if front_data["surname"] == "Not Found" and len(parts) > 3: 
                    front_data["surname"] = parts[3].split(' ')[-1] if ' ' in parts[3] else parts[1]
                if front_data["father_name"] == "Not Found": 
                    front_data["father_name"] = parts[1]
                if front_data["mother_info"] == "Not Found": 
                    front_data["mother_info"] = parts[2]
                if front_data["place_and_date_of_birth"] == "Not Found": 
                    front_data["place_and_date_of_birth"] = parts[4]
                if front_data["national_number"] == "Not Found": 
                    front_data["national_number"] = parts[5]
        
        return {
            "status": "success",
            "extracted_data": {
                "front_side": front_data,
                "back_side": back_data,
                "barcode_decoded_payload": decoded_barcode_str
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import FastAPI, UploadFile, HTTPException
import cv2
import numpy as np
import zxing
import os
from paddleocr import PaddleOCR

app = FastAPI()
reader = zxing.BarCodeReader()
ocr = PaddleOCR(use_angle_cls=True, lang='ar', show_log=False)

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

def decode_barcode_raw(image_bytes: bytes) -> str:
    """Extracts the raw string directly from the barcode without fixing encoding yet."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return ""

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
        
    return barcode.parsed if barcode else ""

def fix_and_parse_barcode(raw_str: str) -> dict:
    """Decodes string bytes safely to Windows-1256 Arabic and breaks down demographic fields."""
    try:
        # Step 1: Decode text payload cleanly, ignoring the non-text trailing binary security fields
        cleaned_text = raw_str.encode('latin1', errors='ignore').decode('windows-1256', errors='ignore')
        
        # Step 2: Extract sections delimited by '#'
        parts = cleaned_text.split('#')
        
        if len(parts) >= 6:
            return {
                "first_name": parts[0].strip(),
                "father_name": parts[1].strip(),
                "mother_name": parts[2].strip(),
                "full_name_lineage": parts[3].strip(),
                "place_and_date_of_birth": parts[4].strip(),
                "national_number": parts[5].strip()
            }
    except Exception as e:
        print(f"Barcode processing fallback warning: {e}")
    return None


@app.post("/api/extract-id-complete")
async def extract_full_id(front_file: UploadFile, back_file: UploadFile):
    try:
        front_bytes = await front_file.read()
        back_bytes = await back_file.read()
        
        # 1. Fetch text data from front and back side using OCR
        front_lines = extract_text_lines(front_bytes)
        back_lines = extract_text_lines(back_bytes)
        
        front_data = parse_front_side(front_lines)
        back_data = parse_back_side(back_lines)
        
        # 2. Decode Barcode structure
        raw_barcode_string = decode_barcode_raw(back_bytes)
        barcode_parsed_dict = fix_and_parse_barcode(raw_barcode_string) if raw_barcode_string else None
        
        # 3. Smart Fallback Layer: If barcode translated cleanly, overwrite missing visual fields
        if barcode_parsed_dict:
            if front_data["first_name"] == "Not Found": 
                front_data["first_name"] = barcode_parsed_dict["first_name"]
            if front_data["father_name"] == "Not Found": 
                front_data["father_name"] = barcode_parsed_dict["father_name"]
            if front_data["mother_info"] == "Not Found": 
                front_data["mother_info"] = barcode_parsed_dict["mother_name"]
            if front_data["surname"] == "Not Found":
                # Fallback to extract surname from full name lineage block if distinct field isn't present
                full_name = barcode_parsed_dict["full_name_lineage"]
                front_data["surname"] = full_name.split(' ')[-1] if ' ' in full_name else full_name
            if front_data["place_and_date_of_birth"] == "Not Found": 
                front_data["place_and_date_of_birth"] = barcode_parsed_dict["place_and_date_of_birth"]
            if front_data["national_number"] == "Not Found": 
                front_data["national_number"] = barcode_parsed_dict["national_number"]
        
        return {
            "status": "success",
            "extracted_data": {
                "front_side": front_data,
                "back_side": back_data,
                "barcode_demographics": barcode_parsed_dict or "Not Readable"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

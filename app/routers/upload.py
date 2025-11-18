from fastapi import APIRouter, UploadFile, File, HTTPException
import os

from ..services.file_upload_service import save_upload_file

router = APIRouter()

@router.post("/upload/")
def upload_file(file: UploadFile = File(...)):
    """
    Accepts a file upload, saves it to the 'uploads' directory,
    and returns the path to the saved file. This endpoint ONLY handles the upload.
    """
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, file.filename)

    try:
        save_upload_file(upload_file=file, destination=file_location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return {
        "message": "File uploaded successfully. Use the returned path to process the file.",
        "file_path": file_location
    }

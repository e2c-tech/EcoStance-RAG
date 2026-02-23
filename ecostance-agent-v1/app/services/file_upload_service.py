from fastapi import UploadFile
import shutil
import aiofiles
import os

def save_upload_file(upload_file: UploadFile, destination: str):
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    finally:
        upload_file.file.close()

async def save_upload_file_async(upload_file: UploadFile, destination: str, chunk_size: int = 1024 * 1024):
    """
    Asynchronously saves an uploaded file to a destination in chunks.
    """
    try:
        async with aiofiles.open(destination, 'wb') as out_file:
            while content := await upload_file.read(chunk_size):
                await out_file.write(content)
    finally:
        await upload_file.close()

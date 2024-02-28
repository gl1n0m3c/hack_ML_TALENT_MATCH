from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List

app = FastAPI()

@app.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    for file in files:
        if file.content_type not in ["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

        filename = f"uploaded_{file.filename}"
        with open(filename, "wb") as buffer:
            buffer.write(await file.read())
    return {"filenames": [file.filename for file in files]}


from app import app  # noqa: F401 — required for `uvicorn main:app`

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080)

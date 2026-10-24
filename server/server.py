"""Label review service.

Usage:  python server/server.py --package sample_package --reviewer tunahan
"""
import argparse

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Label Review Tool")


@app.get("/api/hello")
def hello():
    return {"message": "merhaba"}


def main():
    parser = argparse.ArgumentParser(description="Label review service")
    parser.add_argument("--package", default="sample_package", help="package folder")
    parser.add_argument("--reviewer", default="unknown", help="reviewer name")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()

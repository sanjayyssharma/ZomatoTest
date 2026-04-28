import uvicorn


def main():
    print("Starting Phase 3 Recommender Web API on http://localhost:8000")
    uvicorn.run("phase3.api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()

import os
from fastapi import FastAPI, Header, Query, HTTPException
from fastapi.responses import PlainTextResponse

import requests

app = FastAPI()

SECRET_KEY = os.environ.get("SECRET_TRIGGER_KEY")  # Replace with GitLab CI/CD for prod
HOST_TRIGGER = "http://host-trigger:9001"  # ← this is the internal hostname

STATUS_PATH = "/status"
VALID_ENVS = {"dev", "staging", "prod"}


@app.get("/trigger")
def trigger(secret: str = Header(None), action: str = Query(...), environment: str = Query(...)):
    if secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail=f"Forbidden")

    try:
        response = requests.get(
            f"{HOST_TRIGGER}/?action={action}&environment={environment}",
            headers={"secret": SECRET_KEY},
            timeout=5,
        )
        response.raise_for_status()
        return {"message": response.text.strip()}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Host trigger failed: {e}")


@app.get("/health", response_class=PlainTextResponse)
def root_health():
    return PlainTextResponse("Server is running")


# LOGS are not displayed for security reasons
# def get_log_tail(log_file: str, lines: int = 20) -> str:
#     if os.path.exists(log_file):
#         with open(log_file) as lf:
#             return "".join(lf.readlines()[-lines:])
#     return "No logs available"

# log_tail = get_log_tail(log_file)

# return PlainTextResponse(
#     f"✅ {environment} is {status}\n\nLast logs:\n{log_tail}",
#     status_code=200
# )


def get_health(environment: str) -> PlainTextResponse:
    if environment not in VALID_ENVS:
        raise HTTPException(status_code=404, detail="Environment not found")

    status_file = os.path.join(STATUS_PATH, f"{environment}.status")
    log_file = os.path.join(STATUS_PATH, f"{environment}.log")

    if not os.path.exists(status_file):
        return PlainTextResponse(f"❗ No status available for '{environment}'", status_code=200)

    with open(status_file) as f:
        status = f.read().strip()

    if status in ("building", "starting"):
        return PlainTextResponse(f"⏳ {status.capitalize()} in progress", status_code=206)

    if status == "failed":
        log_tail = "No logs available"
        if os.path.exists(log_file):
            with open(log_file) as lf:
                log_tail = "".join(lf.readlines()[-20:])
        return PlainTextResponse(f"❌ {environment} failed\n\nLogs:\n{log_tail}", status_code=503)

    if status in ("built", "running"):
        return PlainTextResponse(f"✅ {environment} is {status}", status_code=200)

    return PlainTextResponse(f"⚠️ Unknown status: {status}", status_code=500)


@app.get("/health/{environment}", response_class=PlainTextResponse)
@app.get("/health/{environment}/", response_class=PlainTextResponse)
def health_check(environment: str):
    return get_health(environment)

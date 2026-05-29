# host-trigger.py
import os;
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

#### env is loaded in one place in the traefik-start.sh script and passes env variables to this
load_dotenv(dotenv_path=os.environ.get("TRAEFIK_ENV_PATH", "./traefik/.env"))

SECRET = os.environ.get("SECRET_TRIGGER_KEY")
ADMIN_URL = os.environ.get("ADMIN_URL")

VALID_ACTIONS = ["start", "build", "stop"]
VALID_ENVS = ["dev", "staging", "prod"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_components = parse_qs(parsed_url.query)

        action = query_components.get("action", [None])[0]
        environment = query_components.get("environment", [None])[0]

        # ✅ Extract secret from headers
        key = self.headers.get("secret")

        # self.wfile.write(f"KEY: {key}\n".encode("utf-8"))
        # self.wfile.write(f"ACTION: {action}\n".encode("utf-8"))
        # self.wfile.write(f"ENV: {environment}\n".encode("utf-8"))

        if key != SECRET:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden\n")
            # self.wfile.write(f"Forbidden {key}\n".encode("utf-8"))
            return

        if action not in VALID_ACTIONS or environment not in VALID_ENVS:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid action or environment\n")
            return

        # Determine script and arguments
        if action in ["start", "build"]:
            cmd = ["./dalia-start.sh", environment, action]
        elif action == "stop":
            cmd = ["./dalia-stop.sh", environment]

        try:
            subprocess.Popen(cmd)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"{action}-{environment} triggered\nCheck status: {ADMIN_URL}/health/{environment}/\n".encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}\n".encode())

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9001), Handler)
    print("Host listener running on http://0.0.0.0:9001")
    server.serve_forever()

#!/bin/bash

# List of images to preserve
PRESERVE_IMAGES=(
  "docker.io/stain/jena-fuseki:latest"
  "node:18-alpine"
  "traefik:latest"
  "docker.io/library/python:3.9-slim"
)

# Function to check if an image is in the preserve list
function is_preserved {
  local image_tags=("$@")
  for image_tag in "${image_tags[@]}"; do
    for preserved in "${PRESERVE_IMAGES[@]}"; do
      if [[ "$image_tag" == "$preserved" ]]; then
        return 0
      fi
    done
  done
  return 1
}

PIDFILE="/tmp/host-trigger.pid"
if [[ -f "$PIDFILE" ]]; then
    kill "$(cat $PIDFILE)"
    echo "Stopped host-trigger (PID: $(cat $PIDFILE))"
    rm -f "$PIDFILE"
else
    echo "No PID file found."
fi

# Stop and remove all containers defined in the docker-compose file
echo "Stopping and removing all containers..."
podman-compose -f ./traefik-compose.yml -p "traefik" down admin-server
podman-compose -f ./traefik-compose.yml -p "traefik" down maintenance-server
podman-compose -f ./traefik-compose.yml -p "traefik" down traefik

# Remove all stopped containers
echo "Removing all stopped containers if not removed by podman-compose down..."
podman rm $(podman ps -a -q)

echo "Removing all unused images except preserved ones..."
for image in $(podman images -q); do
  # Get all tags for the image
  image_tags=($(podman inspect --format '{{range .RepoTags}}{{.}} {{end}}' $image))
  if ! is_preserved "${image_tags[@]}"; then
    podman rmi $image
  else
    echo "Preserving image: ${image_tags[*]}"
  fi
done

echo "Traefik stopped."

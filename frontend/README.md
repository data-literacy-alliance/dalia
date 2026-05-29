## Local Setup

1. Copy `.env_template` to `.env` file. Set all values in the env files.
2. ```bash
    npm install
    npm run dev
    ```

## Deployment
1. Copy `.env_template` to `.env` file. Set all values in the env files.
2. A sample `docker-compose.yml` is created. You can extend the docker based on this file. *Please make sure that backend is accessible from inside the docker*. 
3. ```bash
   docker compose up --build
   ```

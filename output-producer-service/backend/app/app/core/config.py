import os

# DATABASE SETTINGS
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
)

# CORS SETTINGS
# a string of origins separated by commas, e.g: "http://localhost, http://localhost:4200"
BACKEND_CORS_ORIGINS = os.getenv(
    "BACKEND_CORS_ORIGINS"
)

# VERSION SETTINGS
REVISION = os.getenv("REVISION")
TAG = os.getenv("TAG")
STACK_NAME = os.getenv("STACK_NAME")
DEPLOYED_AT = os.getenv("DEPLOYED_AT")

from pydantic_settings import BaseSettings
from pydantic import field_validator, computed_field
from typing import Optional, List


class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "RBAC Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "rbac_user"
    POSTGRES_PASSWORD: str = "rbac_password"
    POSTGRES_DB: str = "rbac_app"
    POSTGRES_PORT: int = 5432
    
    @computed_field
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # Construir URL de conexión
        if self.POSTGRES_PASSWORD:
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        else:
            return f"postgresql://{self.POSTGRES_USER}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Rate limiting
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_REFRESH: str = "30/minute"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"]
    
    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError(v)
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


settings = Settings()

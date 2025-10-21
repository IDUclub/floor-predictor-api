"""Authentication dependency is defined here."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Define HTTP Bearer authentication scheme
http_bearer = HTTPBearer()


def _get_token_from_header(credentials: HTTPAuthorizationCredentials) -> str:
    """
    Extract and validate the bearer token from the authorization header.

    Args:
        credentials (HTTPAuthorizationCredentials): The credentials extracted by FastAPI's HTTPBearer dependency.

    Returns:
        str: The token string extracted from the Authorization header.

    Raises:
        HTTPException: If the Authorization header or token is missing.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
        )

    token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header",
        )

    return token


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> str:
    """
    Verify and return the bearer token from the HTTP Authorization header.

    This function is designed to be used as a FastAPI dependency.
    It ensures that a valid Authorization header is provided and extracts the token value.

    Example:
        ```
        @app.get("/protected")
        async def protected_route(token: str = Depends(verify_token)):
            return {"token": token}
        ```

    Args:
        credentials (HTTPAuthorizationCredentials): Automatically injected by FastAPI using HTTPBearer.

    Returns:
        str: The validated bearer token.
    """
    return _get_token_from_header(credentials)

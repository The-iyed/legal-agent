from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Get the current user from the token.
    For now, this is a mock implementation that returns a test user.
    In a real application, you would validate the token and get the user from the database.
    """
    # TODO: Implement proper token validation and user retrieval
    # For now, return a mock user
    return {
        "id": "test_user_id",
        "username": "test_user",
        "email": "test@example.com"
    } 
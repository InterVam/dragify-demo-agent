import uuid
import hashlib
import time
from typing import Optional
from fastapi import Request, HTTPException

class SessionManager:
    """
    Simple session management for basic user isolation
    Uses browser fingerprinting and session tokens
    """
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a unique session ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def create_browser_fingerprint(request: Request) -> str:
        """
        Create a simple browser fingerprint for additional session validation
        This is not for security, just for basic user separation
        """
        user_agent = request.headers.get("user-agent", "")
        accept_language = request.headers.get("accept-language", "")
        accept_encoding = request.headers.get("accept-encoding", "")
        
        # Create a simple hash of browser characteristics
        fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
    
    @staticmethod
    def get_session_id_from_request(request: Request) -> Optional[str]:
        """
        Extract session ID from request headers
        Frontend should send this in X-Session-ID header
        """
        return request.headers.get("x-session-id")
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """
        Basic validation of session ID format
        """
        if not session_id or len(session_id) < 10:
            return False
        
        # Check if it's a valid UUID format (for new sessions)
        try:
            uuid.UUID(session_id)
            return True
        except ValueError:
            # Allow legacy sessions and other formats
            return len(session_id) >= 10
    
    @staticmethod
    def require_session_id(request: Request) -> str:
        """
        Get session ID from request or raise HTTP exception
        """
        session_id = SessionManager.get_session_id_from_request(request)
        
        if not session_id:
            raise HTTPException(
                status_code=401, 
                detail="Session ID required. Please refresh the page."
            )
        
        if not SessionManager.validate_session_id(session_id):
            raise HTTPException(
                status_code=401, 
                detail="Invalid session ID. Please refresh the page."
            )
        
        return session_id 
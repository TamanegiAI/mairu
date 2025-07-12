"""File-based token storage service."""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

# Path to token storage file (in root directory)
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'token.json')

class TokenStore:
    """Simple file-based token storage service."""
    
    @staticmethod
    def save_tokens(access_token: Optional[str], refresh_token: Optional[str], expiry: Optional[datetime] = None, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Save tokens to file."""
        token_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expiry': expiry.isoformat() if expiry else None,
            'created_at': datetime.utcnow().isoformat(),
            'scopes': scopes or []
        }
        
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
            print(f"✅ Tokens saved to {TOKEN_FILE}")
            return token_data
        except Exception as e:
            print(f"❌ Failed to save tokens to file: {str(e)}")
            return {}
    
    @staticmethod
    def get_latest_tokens() -> Dict[str, Any]:
        """Get the most recent tokens from file."""
        if not os.path.exists(TOKEN_FILE):
            return {}
            
        try:
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            return {
                'token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
                'expiry': tokens.get('expiry'),
                'created_at': tokens.get('created_at'),
                'scopes': tokens.get('scopes', [])
            }
        except Exception as e:
            print(f"❌ Failed to read tokens from file: {str(e)}")
            return {}
    
    @staticmethod
    def clear_tokens() -> bool:
        """Clear stored tokens."""
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
                print(f"✅ Token file removed: {TOKEN_FILE}")
                return True
            except Exception as e:
                print(f"❌ Failed to remove token file: {str(e)}")
                return False
        return True  # No file to remove
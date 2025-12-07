"""
===============================================================================
Waiting The Longest™ - Authentication Module
===============================================================================
Purpose: Handles OAuth2 authentication flow for Google, Facebook, etc.
         Manages user sessions and token exchange.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-12-06
Dependencies: authlib, starlette
Related Files: main.py, models.py, config.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md
===============================================================================
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .config import settings
from .database import get_db
from .models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize OAuth registry
oauth = OAuth()

# Register Google
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Register Facebook
if settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET:
    oauth.register(
        name='facebook',
        client_id=settings.FACEBOOK_CLIENT_ID,
        client_secret=settings.FACEBOOK_CLIENT_SECRET,
        access_token_url='https://graph.facebook.com/oauth/access_token',
        access_token_params={'grant_type': 'client_credentials'},
        authorize_url='https://www.facebook.com/dialog/oauth',
        api_base_url='https://graph.facebook.com/',
        client_kwargs={'scope': 'email public_profile'}
    )


@router.get("/login/{provider}")
async def login(request: Request, provider: str):
    """
    Initiate OAuth login flow for the specified provider.
    """
    # Validate provider
    if provider not in ['google', 'facebook']:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    # Check if provider is configured
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=501, detail=f"Provider {provider} not configured")
    
    # Build redirect URL
    redirect_uri = request.url_for('auth_callback', provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(request: Request, provider: str, db: Session = Depends(get_db)):
    """
    Handle OAuth callback, create/update user, and set session.
    """
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=400, detail="Invalid provider")
        
    try:
        token = await client.authorize_access_token(request)
    except OAuthError as error:
        return JSONResponse(status_code=401, content={"detail": f"Auth failed: {error.description}"})
        
    user_info = None
    
    if provider == 'google':
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback if userinfo not in token
            user_info = await client.userinfo(token=token)
            
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')
        provider_id = user_info.get('sub')
        
    elif provider == 'facebook':
        # Facebook requires a separate call to get user info
        resp = await client.get('me?fields=id,name,email,picture', token=token)
        user_info = resp.json()
        
        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture', {}).get('data', {}).get('url')
        provider_id = user_info.get('id')
    
    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from provider")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user
        user = User(
            email=email,
            full_name=name,
            picture=picture,
            provider=provider,
            provider_id=provider_id,
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing user
        user.last_login = datetime.now(timezone.utc)
        user.picture = picture # Update picture if changed
        user.full_name = name
        db.commit()
    
    # Set session
    request.session['user'] = {
        'id': user.id,
        'email': user.email,
        'name': user.full_name,
        'picture': user.picture,
        'is_admin': user.is_admin
    }
    
    # Redirect to frontend
    return RedirectResponse(url='/')


@router.get("/logout")
async def logout(request: Request):
    """
    Clear user session.
    """
    request.session.pop('user', None)
    return RedirectResponse(url='/')


@router.get("/me")
async def get_current_user(request: Request):
    """
    Get currently logged in user info.
    """
    user = request.session.get('user')
    if not user:
        return JSONResponse(content={"authenticated": False})
    
    return JSONResponse(content={
        "authenticated": True,
        "user": user
    })

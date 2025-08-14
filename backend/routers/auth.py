from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Body
from sqlmodel import Session, select

from models import User, UserCreate, UserLogin, Token, UserResponse
from auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_database_engine():
    """Get the database engine from the main app context"""
    from fastapi_app import database_engine
    return database_engine

@router.post("/register", 
          summary="Register user", 
          description="Creates a new user account with password authentication.",
          response_model=UserResponse)
def register_user(user_data: UserCreate = Body(..., description="User registration data")):
    """
    Create a new user account with password authentication.
    """
    with Session(get_database_engine()) as session:
        # Check if user already exists
        existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="User with this email already exists")
        
        # Hash password and create user
        password_hash = get_password_hash(user_data.password)
        user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=password_hash
        )
        
        try:
            # Create user
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Return user response without password hash
            return UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                prefered_language=user.prefered_language,
                last_login=user.last_login,
                created_at=user.created_at
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@router.post("/login", 
          summary="Login user", 
          description="Authenticate user with email and password, returns JWT token.",
          response_model=Token)
def login_user(login_data: UserLogin = Body(..., description="User login credentials")):
    """
    Authenticate user and return JWT access token.
    """
    with Session(get_database_engine()) as session:
        user = authenticate_user(login_data.email, login_data.password, session)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last login
        user.last_login = datetime.now()
        session.add(user)
        session.commit()
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")
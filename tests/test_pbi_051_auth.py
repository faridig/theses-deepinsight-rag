import pytest
from unittest.mock import MagicMock
from main_ui import auth_callback, chat_profile

@pytest.mark.asyncio
async def test_auth_callback_always_user():
    user = await auth_callback("admin", "password")
    assert user.metadata["role"] == "USER"
    
    user = await auth_callback("guest", "guest")
    assert user.metadata["role"] == "USER"

@pytest.mark.asyncio
async def test_chat_profiles_always_single():
    user = MagicMock()
    user.metadata = {"role": "USER"}
    profiles = await chat_profile(user)
    assert len(profiles) == 1
    assert profiles[0].name == "RAG Assistant"
    
    admin_user = MagicMock()
    admin_user.metadata = {"role": "ADMIN"} # Even if metadata says ADMIN (from old session)
    profiles = await chat_profile(admin_user)
    assert len(profiles) == 1

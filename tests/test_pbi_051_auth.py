import pytest
import os
from unittest.mock import MagicMock, patch
from main_ui import auth_callback, chat_profile

@pytest.mark.asyncio
async def test_auth_callback_admin():
    with patch.dict(os.environ, {"ADMIN_USER": "admin", "ADMIN_PASSWORD": "password"}):
        user = await auth_callback("admin", "password")
        assert user.identifier == "admin"
        assert user.metadata["role"] == "ADMIN"

@pytest.mark.asyncio
async def test_auth_callback_user():
    user = await auth_callback("guest", "guest")
    assert user.identifier == "guest"
    assert user.metadata["role"] == "USER"

@pytest.mark.asyncio
async def test_chat_profiles_admin():
    admin_user = MagicMock()
    admin_user.metadata = {"role": "ADMIN"}
    profiles = await chat_profile(admin_user)
    assert len(profiles) == 2
    assert profiles[0].name == "RAG Assistant"
    assert profiles[1].name == "Admin Cockpit"

@pytest.mark.asyncio
async def test_chat_profiles_user():
    user = MagicMock()
    user.metadata = {"role": "USER"}
    profiles = await chat_profile(user)
    assert len(profiles) == 1
    assert profiles[0].name == "RAG Assistant"

# -*- coding: utf-8 -*-
"""登录认证路由。"""
import secrets

from fastapi import APIRouter, HTTPException, Request

from app import storage
from app.state import PLATFORM_PASSWORD, PLATFORM_USER

router = APIRouter()


@router.post('/api/login')
async def login(req: Request):
    """登录：校验账号密码，签发会话 token（落库持久化）。"""
    body = await req.json()
    username = body.get('username') or ''
    pwd = body.get('password') or ''
    if PLATFORM_PASSWORD and username == PLATFORM_USER and pwd == PLATFORM_PASSWORD:
        token = secrets.token_hex(16)
        storage.save_session(token)
        return {'ok': True, 'token': token}
    raise HTTPException(401, '账号或密码错误')

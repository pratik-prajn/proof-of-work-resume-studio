"""Internal boundary, scoped session tokens and bounded HTTP request bodies."""
import hmac
import json
from fastapi import Header, HTTPException
import jwt
from .config import settings

MAX_BODY = 2 * 1024 * 1024

async def internal_boundary(x_internal_key: str = Header(default='')):
    if not hmac.compare_digest(x_internal_key, settings().internal_key):
        raise HTTPException(401, 'Use the application frontend.')

async def authenticated_owner(authorization: str = Header(default='')) -> str:
    if not settings().history_enabled:
        raise HTTPException(403, 'Saved history is disabled by the administrator.')
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Sign in to use saved history.')
    try:
        payload = jwt.decode(authorization[7:], settings().token_secret, algorithms=['HS256'],
                             audience='resume-api', issuer='resume-web',
                             options={'require': ['sub', 'exp', 'iat', 'aud', 'iss']})
        subject = payload['sub']
        if not isinstance(subject, str) or not subject.startswith('github:') or len(subject) > 128:
            raise ValueError('Invalid subject.')
        return subject
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, 'Session expired or invalid.') from None

class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            total += len(message.get('body', b''))
            if total > MAX_BODY:
                body = json.dumps({'detail': 'Request exceeds the 2 MB limit.'}).encode()
                await send({'type': 'http.response.start', 'status': 413, 'headers': [(b'content-type', b'application/json')]})
                await send({'type': 'http.response.body', 'body': body})
                return
            chunks.append(message.get('body', b''))
            if not message.get('more_body', False):
                break
        delivered = False
        async def limited_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        return await self.app(scope, limited_receive, send)

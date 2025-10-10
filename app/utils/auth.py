# app/utils/auth.py
from fastapi import Request

def parse_user_ctx(request: Request):
    uid = request.headers.get("X-User-Id")
    gid = request.headers.get("X-User-Group")
    user_id = int(uid) if (uid and uid.isdigit()) else None
    usergroup_id = int(gid) if (gid and gid.isdigit()) else None
    return user_id, usergroup_id

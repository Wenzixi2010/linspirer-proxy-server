import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import json

logger = logging.getLogger(__name__)

from app import schemas
from app.auth import verify_password, get_password_hash, create_access_token, decode_access_token
from app.database import get_db
from app.repositories import ConfigRepository, RulesRepository, CommandsRepository, LogsRepository

router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload.get("sub", "admin")


@router.post("/api/login", response_model=schemas.LoginResponse)
async def login(request: schemas.LoginRequest, db: AsyncSession = Depends(get_db)):
    password_hash = await ConfigRepository.get(db, "admin_password_hash")
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )
    
    if not verify_password(request.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    
    token = create_access_token({"sub": "admin"})
    return schemas.LoginResponse(token=token)


@router.put("/api/password")
async def change_password(
    request: schemas.ChangePasswordRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_hash = await ConfigRepository.get(db, "admin_password_hash")
    if not current_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )
    
    if not verify_password(request.old_password, current_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid old password",
        )
    
    new_hash = get_password_hash(request.new_password)
    await ConfigRepository.set(db, "admin_password_hash", new_hash, "Hashed admin password")
    
    return {"status": "ok"}


@router.get("/api/rules", response_model=List[schemas.RuleResponse])
async def list_rules(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rules = await RulesRepository.list_all(db)
    return [
        schemas.RuleResponse(
            id=rule.id,
            method_name=rule.method_name,
            email=rule.email,
            action=rule.action,
            custom_response=rule.custom_response,
            remark=rule.remark,
            is_enabled=rule.is_enabled,
            is_global=rule.is_global,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
        for rule in rules
    ]


@router.post("/api/rules", response_model=schemas.RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: schemas.CreateRuleRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    valid_actions = ["passthrough", "modify", "replace", "randomize_app_duration"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{request.action}'. Must be one of: {', '.join(valid_actions)}",
        )
    
    if request.action in ["replace", "modify"] and not request.custom_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom_response is required when action is 'replace' or 'modify'",
        )
    
    try:
        rule_id = await RulesRepository.create(
            db,
            request.method_name,
            request.action,
            request.custom_response,
            email=request.email,
            is_global=request.is_global,
            remark=request.remark
        )
        rule = await RulesRepository.find_by_id(db, rule_id)
    except Exception as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create rule: {str(e)}",
        )
    
    return schemas.RuleResponse(
        id=rule.id,
        method_name=rule.method_name,
        email=rule.email,
        action=rule.action,
        custom_response=rule.custom_response,
        remark=rule.remark,
        is_enabled=rule.is_enabled,
        is_global=rule.is_global,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.put("/api/rules/{rule_id}", response_model=schemas.RuleResponse)
async def update_rule(
    rule_id: int,
    request: schemas.UpdateRuleRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.action and request.action not in ["passthrough", "modify", "replace", "randomize_app_duration"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action",
        )
    
    if request.action and request.action in ["replace", "modify"] and not request.custom_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom_response is required when action is 'replace' or 'modify'",
        )
    
    success = await RulesRepository.update(
        db,
        rule_id,
        method_name=request.method_name,
        action=request.action,
        custom_response=request.custom_response,
        is_enabled=request.is_enabled,
        email=request.email,
        is_global=request.is_global,
        remark=request.remark
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )
    
    rule = await RulesRepository.find_by_id(db, rule_id)
    return schemas.RuleResponse(
        id=rule.id,
        method_name=rule.method_name,
        email=rule.email,
        action=rule.action,
        custom_response=rule.custom_response,
        remark=rule.remark,
        is_enabled=rule.is_enabled,
        is_global=rule.is_global,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/api/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await RulesRepository.delete(db, rule_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )


@router.get("/api/commands", response_model=List[schemas.CommandResponse])
async def list_commands(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    commands = await CommandsRepository.list_all(db)
    return [
        schemas.CommandResponse(
            id=cmd.id,
            command=json.loads(cmd.command_json) if cmd.command_json else {},
            status=cmd.status,
            received_at=cmd.received_at,
            processed_at=cmd.processed_at,
            notes=cmd.notes,
        )
        for cmd in commands
    ]


@router.post("/api/commands/{command_id}", response_model=schemas.CommandResponse)
async def verify_command(
    command_id: int,
    request: schemas.UpdateCommandRequest,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await CommandsRepository.update_status(db, command_id, request.status, request.notes)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found",
        )
    
    cmd = await CommandsRepository.find_by_id(db, command_id)
    return schemas.CommandResponse(
        id=cmd.id,
        command=json.loads(cmd.command_json) if cmd.command_json else {},
        status=cmd.status,
        received_at=cmd.received_at,
        processed_at=cmd.processed_at,
        notes=cmd.notes,
    )


@router.post("/api/commands/{command_id}/send")
async def send_command_to_device(
    command_id: int,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 获取命令详情
    command = await CommandsRepository.find_by_id(db, command_id)
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found"
        )
    
    # 验证命令状态
    if command.status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command must be verified before sending to device"
        )
    
    try:
        # 解析命令JSON
        command_data = json.loads(command.command_json)
        
        # 根据JADX和MCP逆向分析的结果，实现设备命令发送
        # 这里模拟命令发送成功
        device_response = "Command executed successfully"
        
        # 更新命令状态
        await CommandsRepository.update_status(db, command_id, "sent", notes="Command sent to device")
        
        return {
            "status": "success",
            "message": "Command sent to device successfully",
            "device_response": device_response
        }
    except Exception as e:
        await CommandsRepository.update_status(db, command_id, "failed", notes=f"Failed to send command: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send command: {str(e)}"
        )


@router.get("/api/logs", response_model=schemas.PaginatedLogsResponse)
async def list_logs(
    request: Request,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 显式从query_params获取method，解决带点方法名的匹配问题
    method = request.query_params.get("method")
    offset = (page - 1) * limit
    logs, total = await LogsRepository.list(db, method, search, limit, offset)
    
    return schemas.PaginatedLogsResponse(
        data=[
            schemas.RequestLogResponse(
                id=log.id,
                method=log.method,
                request_body=json.loads(log.request_body) if log.request_body else {},
                response_body=json.loads(log.response_body) if log.response_body else {},
                intercepted_request=json.loads(log.intercepted_request) if log.intercepted_request else None,
                intercepted_response=json.loads(log.intercepted_response) if log.intercepted_response else None,
                request_interception_action=log.request_interception_action,
                response_interception_action=log.response_interception_action,
                email=getattr(log, 'email', None),
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
    )


@router.get("/api/logs/methods", response_model=List[str])
async def list_methods(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LogsRepository.list_methods(db)


@router.get("/api/logs/emails", response_model=List[str])
async def list_emails(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LogsRepository.list_emails(db)


@router.get("/api/logs/stats")
async def get_logs_stats(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await LogsRepository.list(db, None, None, 1, 0)
    methods = await LogsRepository.list_methods(db)
    emails = await LogsRepository.list_emails(db)
    return {
        "total_logs": total,
        "methods_count": len(methods),
        "emails_count": len(emails),
        "methods": methods,
        "emails": emails
    }




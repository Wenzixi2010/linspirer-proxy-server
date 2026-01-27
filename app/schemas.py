from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict, Union
from datetime import datetime


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class CreateRuleRequest(BaseModel):
    method_name: str
    email: Optional[str] = None
    action: str
    custom_response: Optional[str] = None
    remark: Optional[str] = None
    is_global: bool = False


class UpdateRuleRequest(BaseModel):
    method_name: Optional[str] = None
    email: Optional[str] = None
    action: Optional[str] = None
    custom_response: Optional[str] = None
    remark: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_global: Optional[bool] = None


class UpdateCommandRequest(BaseModel):
    status: str
    notes: Optional[str] = None


class RuleResponse(BaseModel):
    id: int
    method_name: str
    email: Optional[str] = None
    action: str
    custom_response: Optional[str] = None
    remark: Optional[str] = None
    is_enabled: bool
    is_global: bool
    created_at: datetime
    updated_at: datetime


class CommandResponse(BaseModel):
    id: int
    command: Dict[str, Any]
    status: str
    received_at: datetime
    processed_at: Optional[datetime]
    notes: Optional[str]


class RequestLogResponse(BaseModel):
    id: int
    method: Optional[str]
    request_body: Dict[str, Any]
    response_body: Dict[str, Any]
    intercepted_request: Optional[Dict[str, Any]]
    intercepted_response: Optional[Dict[str, Any]]
    request_interception_action: Optional[str]
    response_interception_action: Optional[str]
    email: Optional[str] = None
    created_at: datetime


class PaginatedLogsResponse(BaseModel):
    data: List[RequestLogResponse]
    total: int


class ApiError(BaseModel):
    error: str


from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional
import json
import logging
import httpx
import random
import time

from app.auth import decode_access_token
from app.crypto import Cryptor
from app.config import get_settings
from app.database import async_session_maker
from app.repositories import LogsRepository, RulesRepository

logger = logging.getLogger(__name__)


async def save_log(
    method: str,
    request_body: str,
    response_body: str,
    intercepted_request: str = None,
    intercepted_response: str = None,
    req_action: str = None,
    resp_action: str = None,
    email: str = None
):
    try:
        async with async_session_maker() as session:
            await LogsRepository.create(
                db=session,
                method=method,
                request_body=request_body,
                response_body=response_body,
                intercepted_request=intercepted_request,
                intercepted_response=intercepted_response,
                request_interception_action=req_action,
                response_interception_action=resp_action,
                email=email
            )
    except Exception as e:
        logger.warning(f"Failed to save log: {e}")


async def check_interception_rule(db_session, method: str, email: Optional[str] = None):
    rule = await RulesRepository.find_by_method(db_session, method, email)
    return rule



class ProxyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, cryptor: Cryptor):
        super().__init__(app)
        self.cryptor = cryptor
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/public-interface.php":
            return await call_next(request)
        
        body = await request.body()
        body_str = body.decode("utf-8", errors="replace")
        
        if not body_str:
            return await call_next(request)
        
        try:
            request_json = json.loads(body_str)
        except json.JSONDecodeError:
            return await call_next(request)
        
        original_request = body_str
        self.decrypt_params(request_json)
        method = request_json.get("method", "")
        
        params = request_json.get("params", {})
        email = None
        email_fields = ["email", "userEmail", "user_email", "username", "userId", "user_id", "user"]
        if isinstance(params, dict):
            for field in email_fields:
                email = params.get(field)
                if email:
                    break
        elif isinstance(params, str):
            try:
                params_obj = json.loads(params)
                if isinstance(params_obj, dict):
                    for field in email_fields:
                        email = params_obj.get(field)
                        if email:
                            break
            except:
                pass
        
        async with async_session_maker() as db_session:
            rule = await check_interception_rule(db_session, method, email)
            
            intercepted_req = None
            req_action = None
            
            if rule:
                logger.info(f"Found interception rule for method '{method}': action={rule.action}")
                
                if rule.action == "replace":
                    try:
                        custom_response = json.loads(rule.custom_response) if rule.custom_response else {}
                        custom_response_str = json.dumps(custom_response)
                        encrypted_response = self.cryptor.encrypt(custom_response_str)
                        
                        logger.info(f"Replace rule applied for method={method}, saving log with replace action")
                        
                        await save_log(
                            method=method,
                            request_body=json.dumps(request_json),
                            response_body=custom_response_str,
                            intercepted_request=json.dumps(request_json),
                            intercepted_response=custom_response_str,
                            req_action=None,
                            resp_action="replace",
                            email=email
                        )
                        
                        return Response(
                            content=encrypted_response,
                            status_code=200,
                            headers={"Content-Type": "application/json"},
                        )
                    except Exception as e:
                        logger.error(f"Failed to apply replace rule: {e}")
                
                elif rule.action == "modify":
                    try:
                        custom_request = json.loads(rule.custom_response) if rule.custom_response else {}
                        modified_request = custom_request
                        request_body_for_log = json.dumps(request_json)
                        intercepted_req = json.dumps(modified_request)
                        req_action = "modify"
                        encrypted_request_body = self.encrypt_request_json(modified_request)
                        logger.info(f"Modify rule applied for method={method}, saving log with modify action")
                    except Exception as e:
                        logger.error(f"Failed to apply modify rule: {e}")
                        request_body_for_log = json.dumps(request_json)
                        encrypted_request_body = self.encrypt_request_json(request_json)
                
                elif rule.action == "randomize_app_duration":
                    try:
                        modified_request = self.randomize_app_duration(request_json, rule.custom_response)
                        request_body_for_log = json.dumps(request_json)
                        intercepted_req = json.dumps(modified_request)
                        req_action = "randomize_app_duration"
                        encrypted_request_body = self.encrypt_request_json(modified_request)
                        logger.info(f"Randomize app duration rule applied for method={method}")
                    except Exception as e:
                        logger.error(f"Failed to apply randomize app duration rule: {e}")
                        request_body_for_log = json.dumps(request_json)
                        encrypted_request_body = self.encrypt_request_json(request_json)
            
            else:
                # 没有规则时，使用原始请求
                request_body_for_log = json.dumps(request_json)
                encrypted_request_body = self.encrypt_request_json(request_json)
            
            target_url = self.settings.LINSPIRER_TARGET_URL + request.url.path
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                try:
                    target_response = await client.post(
                        target_url,
                        content=encrypted_request_body,
                        headers={"Content-Type": "application/json"},
                    )
                    
                    response_body = target_response.text
                    
                    try:
                        decrypted_response = self.cryptor.decrypt(response_body)
                    except Exception as e:
                        logger.warning(f"Failed to decrypt response: {e}. Using original response.")
                        decrypted_response = response_body
                    
                    intercepted_resp = None
                    resp_action = None
                    
                    # 只有replace动作才修改响应
                    if rule and rule.action == "replace":
                        try:
                            custom_response = json.loads(rule.custom_response) if rule.custom_response else {}
                            decrypted_response = json.dumps(custom_response)
                            intercepted_resp = decrypted_response
                            resp_action = rule.action
                        except Exception as e:
                            logger.error(f"Failed to apply replace rule to response: {e}")
                    
                    try:
                        encrypted_response = self.cryptor.encrypt(decrypted_response)
                    except Exception as e:
                        logger.warning(f"Failed to encrypt response: {e}")
                        encrypted_response = response_body
                    
                    logger.info(f"Saving log: method={method}, req_action={req_action}, resp_action={resp_action}")
                    
                    await save_log(
                        method=method,
                        request_body=request_body_for_log,
                        response_body=decrypted_response,
                        intercepted_request=intercepted_req,
                        intercepted_response=intercepted_resp,
                        req_action=req_action,
                        resp_action=resp_action,
                        email=email
                    )
                    
                    return Response(
                        content=encrypted_response,
                        status_code=target_response.status_code,
                        headers={"Content-Type": "application/json"},
                    )
                except httpx.RequestError as e:
                    logger.error(f"Proxy error: {e}")
                    return JSONResponse(
                        status_code=502,
                        content={"error": f"Failed to connect to target: {str(e)}"},
                    )
    
    def decrypt_params(self, request: dict):
        if "params" in request and isinstance(request["params"], str):
            try:
                decrypted = self.cryptor.decrypt(request["params"])
                request["params"] = json.loads(decrypted)
            except Exception as e:
                logger.warning(f"Failed to decrypt request params: {e}")
                request["params"] = {"error": "Failed to decrypt params"}
    
    def encrypt_request_json(self, request: dict) -> str:
        # 移除临时规则信息字段，避免发送到目标服务器
        rule_info = request.pop("_rule_info", None)
        
        if "params" in request:
            try:
                params_str = json.dumps(request["params"])
                encrypted = self.cryptor.encrypt(params_str)
                request["params"] = encrypted
            except Exception as e:
                logger.warning(f"Failed to encrypt request params: {e}")
        
        # 将规则信息添加回请求，用于日志记录
        if rule_info:
            request["_rule_info"] = rule_info
        
        return json.dumps(request)
    
    def randomize_app_duration(self, request_json: dict, config_str: str = None) -> dict:
        modified_request = request_json.copy()
        params = modified_request.get("params", {})
        if not isinstance(params, dict):
            return request_json
        
        logs = params.get("logs", [])
        if not logs or not isinstance(logs, list):
            return request_json
        
        try:
            config = json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            config = {}
        
        target_packages = config.get("packages", ["com.kingsoft"])
        max_duration_ms = int(config.get("max_duration_minutes", 30)) * 60 * 1000
        keep_count = config.get("keep_count", 2)
        
        filtered_logs = []
        package_durations = {}
        action_details = []
        
        for log in logs:
            if not isinstance(log, dict):
                continue
            
            package_name = log.get("mPackageName", "")
            if package_name not in target_packages:
                filtered_logs.append(log)
                continue
            
            begin_time = log.get("mBeginTimeStamp", 0)
            end_time = log.get("mEndTimeStamp", 0)
            duration = end_time - begin_time
            
            if package_name not in package_durations:
                package_durations[package_name] = []
            
            package_durations[package_name].append({
                "log": log,
                "duration": duration,
                "begin_time": begin_time
            })
        
        for package, package_logs in package_durations.items():
            if not package_logs:
                continue
            
            long_logs = [p for p in package_logs if p["duration"] > max_duration_ms]
            short_logs = [p for p in package_logs if p["duration"] <= max_duration_ms]
            
            for log_info in long_logs:
                original_duration = log_info["duration"]
                new_duration = random.randint(1, max_duration_ms // 1000) * 1000
                new_end_time = log_info["begin_time"] + new_duration
                
                log_info["log"]["mEndTimeStamp"] = new_end_time
                log_info["log"]["mDuration"] = new_duration
                
                action_details.append({
                    "package": package,
                    "original_duration_ms": original_duration,
                    "new_duration_ms": new_duration,
                    "original_end_time": log_info["begin_time"] + original_duration,
                    "new_end_time": new_end_time
                })
            
            modified_logs = [p["log"] for p in package_logs]
            
            original_count = len(modified_logs)
            if len(modified_logs) > keep_count:
                indices_to_keep = sorted(random.sample(range(len(modified_logs)), keep_count))
                modified_logs = [modified_logs[i] for i in indices_to_keep]
                action_details.append({
                    "action": "reduce_count",
                    "package": package,
                    "original_count": original_count,
                    "new_count": keep_count
                })
            
            filtered_logs.extend(modified_logs)
        
        params["logs"] = filtered_logs
        modified_request["params"] = params
        
        # 添加规则信息到请求中，用于日志记录
        modified_request["_rule_info"] = {
            "method": request_json.get("method", ""),
            "status": "Enabled",
            "action": "randomize_app_duration",
            "type": "全局",
            "config": config,
            "action_details": action_details
        }
        
        logger.info(f"Applied randomize_app_duration rule: {json.dumps(action_details)}")
        return modified_request


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/admin/api/") and not request.url.path == "/admin/api/login":
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing or invalid Authorization header"},
                )
            
            token = auth_header.split(" ")[1]
            payload = decode_access_token(token)
            if payload is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid or expired token"},
                )
        
        return await call_next(request)

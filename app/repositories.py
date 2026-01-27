from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from datetime import datetime
import json

from app.models import Config, InterceptionRule, Command, RequestLog, china_now


class ConfigRepository:
    @staticmethod
    async def get(db: AsyncSession, key: str) -> Optional[str]:
        result = await db.execute(select(Config).where(Config.key == key))
        config = result.scalar_one_or_none()
        return config.value if config else None
    
    @staticmethod
    async def set(db: AsyncSession, key: str, value: str, description: Optional[str] = None) -> None:
        result = await db.execute(select(Config).where(Config.key == key))
        config = result.scalar_one_or_none()
        if config:
            config.value = value
            config.updated_at = china_now()
            if description:
                config.description = description
        else:
            config = Config(key=key, value=value, description=description)
            db.add(config)
        await db.commit()


class RulesRepository:
    @staticmethod
    async def list_all(db: AsyncSession) -> List[InterceptionRule]:
        result = await db.execute(select(InterceptionRule).order_by(InterceptionRule.created_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def find_by_id(db: AsyncSession, id: int) -> Optional[InterceptionRule]:
        result = await db.execute(select(InterceptionRule).where(InterceptionRule.id == id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def find_by_method(db: AsyncSession, method: str, email: Optional[str] = None) -> Optional[InterceptionRule]:
        result = await db.execute(
            select(InterceptionRule)
            .where(InterceptionRule.method_name == method)
            .where(InterceptionRule.is_enabled == True)
            .order_by(InterceptionRule.created_at.desc())
        )
        rules = list(result.scalars().all())
        
        user_rule = None
        for rule in rules:
            if rule.is_global:
                continue
            
            if rule.email:
                rule_emails = [e.strip() for e in rule.email.split(',')]
                if email and email in rule_emails:
                    user_rule = rule
                    break
        
        if user_rule:
            return user_rule
        
        for rule in rules:
            if rule.is_global and not rule.email:
                return rule
        
        return None
    
    @staticmethod
    async def find_global_by_method(db: AsyncSession, method: str) -> Optional[InterceptionRule]:
        result = await db.execute(
            select(InterceptionRule)
            .where(InterceptionRule.method_name == method)
            .where(InterceptionRule.email.is_(None))
            .where(InterceptionRule.is_enabled == True)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def find_by_method_and_email(db: AsyncSession, method: str, email: Optional[str], is_global: bool) -> Optional[InterceptionRule]:
        result = await db.execute(
            select(InterceptionRule)
            .where(InterceptionRule.method_name == method)
            .where(InterceptionRule.email == email if not is_global else None)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(
        db: AsyncSession,
        method_name: str,
        action: str,
        custom_response: Optional[str] = None,
        email: Optional[str] = None,
        is_global: bool = False,
        remark: Optional[str] = None
    ) -> int:
        target_email = None if is_global else email
        existing = await RulesRepository.find_by_method_and_email(db, method_name, target_email, is_global)
        
        if existing:
            await RulesRepository.update(db, existing.id,
                method_name=method_name,
                action=action,
                custom_response=custom_response,
                is_enabled=True,
                email=target_email,
                is_global=is_global,
                remark=remark
            )
            return existing.id
        
        rule = InterceptionRule(
            method_name=method_name,
            action=action,
            custom_response=custom_response,
            email=target_email,
            is_global=is_global,
            is_enabled=True,
            remark=remark
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule.id
    
    @staticmethod
    async def update(
        db: AsyncSession,
        id: int,
        method_name: Optional[str] = None,
        action: Optional[str] = None,
        custom_response: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        email: Optional[str] = None,
        is_global: Optional[bool] = None,
        remark: Optional[str] = None
    ) -> bool:
        result = await db.execute(select(InterceptionRule).where(InterceptionRule.id == id))
        rule = result.scalar_one_or_none()
        if not rule:
            return False
        
        if method_name is not None:
            rule.method_name = method_name
        if action is not None:
            rule.action = action
        if custom_response is not None:
            rule.custom_response = custom_response
        if is_enabled is not None:
            rule.is_enabled = is_enabled
        if email is not None:
            rule.email = email
        if is_global is not None:
            rule.email = None if is_global else rule.email
            rule.is_global = is_global
        if remark is not None:
            rule.remark = remark
        rule.updated_at = china_now()
        
        await db.commit()
        return True
    
    @staticmethod
    async def delete(db: AsyncSession, id: int) -> bool:
        result = await db.execute(select(InterceptionRule).where(InterceptionRule.id == id))
        rule = result.scalar_one_or_none()
        if not rule:
            return False
        
        await db.delete(rule)
        await db.commit()
        return True


class CommandsRepository:
    @staticmethod
    async def list_all(db: AsyncSession) -> List[Command]:
        result = await db.execute(select(Command).order_by(Command.received_at.desc()))
        return list(result.scalars().all())
    
    @staticmethod
    async def list_by_status(db: AsyncSession, status: str) -> List[Command]:
        result = await db.execute(
            select(Command)
            .where(Command.status == status)
            .order_by(Command.received_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def find_by_id(db: AsyncSession, id: int) -> Optional[Command]:
        result = await db.execute(select(Command).where(Command.id == id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def insert(db: AsyncSession, command_json: str, status: str = "unverified") -> int:
        cmd = Command(command_json=command_json, status=status)
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
        return cmd.id
    
    @staticmethod
    async def update_status(db: AsyncSession, id: int, status: str, notes: Optional[str] = None) -> bool:
        result = await db.execute(select(Command).where(Command.id == id))
        cmd = result.scalar_one_or_none()
        if not cmd:
            return False
        
        cmd.status = status
        cmd.processed_at = china_now()
        if notes:
            cmd.notes = notes
        
        await db.commit()
        return True
    
    @staticmethod
    async def clear_verified(db: AsyncSession) -> int:
        result = await db.execute(select(Command).where(Command.status == "verified"))
        cmds = result.scalars().all()
        count = len(cmds)
        for cmd in cmds:
            await db.delete(cmd)
        await db.commit()
        return count


class LogsRepository:
    @staticmethod
    async def list(
        db: AsyncSession,
        method: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[List[RequestLog], int]:
        query = select(RequestLog)
        count_query = select(RequestLog)
        
        if method:
            query = query.where(RequestLog.method == method)
            count_query = count_query.where(RequestLog.method == method)
        
        if search:
            pattern = f"%{search}%"
            query = query.where(
                (RequestLog.request_body.like(pattern)) | 
                (RequestLog.response_body.like(pattern))
            )
            count_query = count_query.where(
                (RequestLog.request_body.like(pattern)) | 
                (RequestLog.response_body.like(pattern))
            )
        
        query = query.order_by(RequestLog.created_at.desc())
        
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        
        result = await db.execute(query)
        logs = list(result.scalars().all())
        
        count_result = await db.execute(count_query)
        total = await db.execute(select(text("COUNT(*)")).select_from(count_query.subquery()))
        total_count = total.scalar() or 0
        
        return logs, total_count
    
    @staticmethod
    async def list_methods(db: AsyncSession) -> List[str]:
        result = await db.execute(
            select(RequestLog.method)
            .distinct()
            .where(RequestLog.method.isnot(None))
            .order_by(RequestLog.method)
        )
        return [m for m in result.scalars().all() if m]
    
    @staticmethod
    async def list_emails(db: AsyncSession) -> List[str]:
        result = await db.execute(
            select(RequestLog.email)
            .distinct()
            .where(RequestLog.email.isnot(None))
            .where(RequestLog.email != '')
            .order_by(RequestLog.email)
        )
        emails = [e for e in result.scalars().all() if e]
        
        if not emails:
            rule_result = await db.execute(
                select(InterceptionRule.email)
                .distinct()
                .where(InterceptionRule.email.isnot(None))
                .where(InterceptionRule.email != '')
            )
            rule_emails = [e for e in rule_result.scalars().all() if e]
            emails = list(set(emails + rule_emails))
            emails.sort()
        
        return emails
    
    @staticmethod
    async def create(
        db: AsyncSession,
        method: str,
        request_body: str,
        response_body: str,
        intercepted_request: Optional[str] = None,
        intercepted_response: Optional[str] = None,
        request_interception_action: Optional[str] = None,
        response_interception_action: Optional[str] = None,
        email: Optional[str] = None
    ) -> int:
        log = RequestLog(
            method=method,
            request_body=request_body,
            response_body=response_body,
            intercepted_request=intercepted_request,
            intercepted_response=intercepted_response,
            request_interception_action=request_interception_action,
            response_interception_action=response_interception_action,
            email=email
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log.id
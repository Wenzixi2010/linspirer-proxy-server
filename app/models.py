from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, CheckConstraint, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
import pytz

Base = declarative_base()

def china_now():
    return datetime.now(pytz.timezone('Asia/Shanghai'))


class Config(Base):
    __tablename__ = "config"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=china_now, onupdate=china_now)


class InterceptionRule(Base):
    __tablename__ = "interception_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    method_name = Column(String, nullable=False)
    email = Column(String, nullable=True, default=None)
    action = Column(String, nullable=False)
    custom_response = Column(Text, nullable=True)
    remark = Column(String, nullable=True, default=None)
    is_enabled = Column(Boolean, default=True)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=china_now)
    updated_at = Column(DateTime, default=china_now, onupdate=china_now)
    
    __table_args__ = (
        CheckConstraint("action IN ('passthrough', 'modify', 'replace', 'randomize_app_duration')", name="check_action"),
        Index('idx_interception_rules_method_email', 'method_name', 'email'),
    )


class Command(Base):
    __tablename__ = "commands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    command_json = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    received_at = Column(DateTime, default=china_now)
    processed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        CheckConstraint("status IN ('unverified', 'verified', 'rejected')", name="check_status"),
    )


class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    method = Column(String, nullable=True)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    intercepted_request = Column(Text, nullable=True)
    intercepted_response = Column(Text, nullable=True)
    request_interception_action = Column(String, nullable=True)
    response_interception_action = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=china_now)




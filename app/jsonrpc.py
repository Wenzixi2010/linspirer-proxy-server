from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime


class InterceptionAction(str, Enum):
    PASSTHROUGH = "passthrough"
    MODIFY = "modify"
    REPLACE = "replace"


class BaseParams(BaseModel):
    email: str
    model: str
    swdid: str


class GetTacticsParams(BaseParams):
    launcher_version: str


class GenericRequestContent(BaseModel):
    method: str
    params: Dict[str, Any] = {}


class RequestContent(BaseModel):
    method: str
    params: Dict[str, Any]


class JsonRpcRequest(BaseModel):
    version: int = Field(..., alias="!version")
    client_version: str
    id: int
    jsonrpc: str = "2.0"
    content: Dict[str, Any]


class TacticsApp(BaseModel):
    id: int
    name: str
    packagename: str
    status: int
    versioncode: int
    versionname: str
    canuninstall: bool
    is_trust: bool
    isforce: bool
    isnew: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    devicetype: Optional[str] = None
    sha1: Optional[str] = None
    target_sdk_version: Optional[int] = None
    sort_weight: Optional[int] = None
    hide_icon_status: Optional[int] = None
    exception_white_url: Optional[int] = None
    grant_to: Optional[int] = None
    grant_type: Optional[int] = None
    groupid: Optional[int] = None


class AppTactics(BaseModel):
    applist: List[TacticsApp]


class LaunchApp(BaseModel):
    launch_mode: int
    launch_package: str


class OtgSet(BaseModel):
    status: int
    pv_list: List[str] = []


class ProtectedEyesStatus(BaseModel):
    distance_status: int
    sensitive_status: int
    sitting_position_status: int


class RemindDuration(BaseModel):
    duration: int
    remind_status: int


class DeviceSetting(BaseModel):
    alarm_clock_status: int
    allow_change_password_status: int
    calendar_status: int
    camera_status: int
    data_flow_status: int
    disable_reinstall_system_status: int
    enable_client_admin_status: int
    enable_gesture_pwd_status: int
    enable_gps_status: int
    enable_screenshots_status: int
    enable_system_upgrade_status: int
    enable_wifi_advanced_status: int
    gallery_status: int
    hide_accelerate_status: int
    hide_cleanup_status: int
    keep_alive_package: Optional[str] = None
    launch_app: Optional[LaunchApp] = None
    logout_status: int
    only_install_store_app_status: int
    otg_set: Optional[OtgSet] = None
    protected_eyes_status: Optional[ProtectedEyesStatus] = None
    remind_duration: Optional[RemindDuration] = None
    rotate_setting_status: int
    school_class_display_status: int
    sdcard_and_otg: int
    show_privacy_statement_status: int
    simcard: int


class DeviceManage(BaseModel):
    command_bluetooth: bool
    command_camera: bool
    command_connect_usb: bool
    command_data_flow: bool
    command_force_open_wifi: bool
    command_gps: bool
    command_otg: bool
    command_phone_msg: bool
    command_recording: bool
    command_sd_card: bool
    command_wifi_advanced: bool
    command_wifi_switch: bool


class DeviceTactics(BaseModel):
    deviceManage: DeviceManage


class WorkspaceTactics(BaseModel):
    worktime: Dict[str, Any] = {}


class IllegalTactics(BaseModel):
    already_root: Dict[str, Any] = {}
    change_simcard: Dict[str, Any] = {}
    prohibited_app: Dict[str, Any] = {}
    usb_to_pc: Dict[str, Any] = {}


class Tactics(BaseModel):
    app_status: bool
    app_tactics: AppTactics
    device_setting: DeviceSetting
    device_status: bool
    device_tactics: DeviceTactics
    enable_amap_status: int
    free_control: int
    id: int
    illegal_status: bool
    illegal_tactics: IllegalTactics
    interest_applist: List[str] = []
    name: str
    release_control: int
    updated_at: Optional[str] = None
    usergroup: int
    wifi_status: bool
    wifi_tactics: List[str] = []
    wifi_tactics_2: List[str] = []
    workspace_status: bool
    workspace_tactics: WorkspaceTactics


class TacticsWrapper(BaseModel):
    type: str = "object"
    data: Tactics


class GenericResponseContent(BaseModel):
    type: str
    data: Any


class JsonRpcResponse(BaseModel):
    code: int
    data: Union[TacticsWrapper, GenericResponseContent]


class CommandItem(BaseModel):
    id: Optional[int] = None
    cmd: Optional[Dict[str, Any]] = None
    cmdstr: Optional[str] = None
    cmdtype: Optional[str] = None
    created_at: Optional[str] = None
    description: Optional[str] = None
    deviceid: Optional[str] = None
    enabletime: Optional[str] = None
    executestatus: Optional[str] = None
    expiretime: Optional[str] = None
    fromuser: Optional[str] = None
    groupid: Optional[int] = None
    level: Optional[int] = None
    needfeedback: Optional[int] = None
    priority: Optional[int] = None
    remark: Optional[str] = None
    sendtime: Optional[str] = None
    status: Optional[str] = None
    taskid: Optional[str] = None
    title: Optional[str] = None
    touser: Optional[str] = None
    type: Optional[str] = None
    usergroup: Optional[int] = None

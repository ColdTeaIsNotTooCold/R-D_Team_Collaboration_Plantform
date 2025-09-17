from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..api.deps import get_current_active_user

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_contexts(
    skip: int = 0,
    limit: int = 100,
    task_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取上下文列表"""
    # TODO: 实现上下文列表查询逻辑
    return [
        {
            "id": 1,
            "task_id": 1,
            "type": "code",
            "content": "def hello_world():\n    print('Hello, World!')",
            "metadata": {"language": "python", "lines": 2},
            "created_at": "2024-01-01T00:00:00Z"
        },
        {
            "id": 2,
            "task_id": 1,
            "type": "requirements",
            "content": "需要添加错误处理和日志记录",
            "metadata": {"priority": "high"},
            "created_at": "2024-01-01T00:00:00Z"
        }
    ]


@router.post("/", response_model=dict)
async def create_context(
    context_data: dict,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新上下文"""
    # TODO: 实现上下文创建逻辑
    return {
        "id": 3,
        "task_id": context_data.get("task_id"),
        "type": context_data.get("type", "text"),
        "content": context_data.get("content", ""),
        "metadata": context_data.get("metadata", {}),
        "created_by": current_user.get("user_id"),
        "created_at": "2024-01-01T00:00:00Z"
    }


@router.get("/{context_id}", response_model=dict)
async def read_context(
    context_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取指定上下文信息"""
    # TODO: 实现上下文查询逻辑
    if context_id == 1:
        return {
            "id": context_id,
            "task_id": 1,
            "type": "code",
            "content": "def hello_world():\n    print('Hello, World!')",
            "metadata": {"language": "python", "lines": 2},
            "created_at": "2024-01-01T00:00:00Z"
        }
    raise HTTPException(status_code=404, detail="Context not found")


@router.put("/{context_id}", response_model=dict)
async def update_context(
    context_id: int,
    context_update: dict,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新上下文"""
    # TODO: 实现上下文更新逻辑
    return {
        "id": context_id,
        "content": context_update.get("content", ""),
        "metadata": context_update.get("metadata", {}),
        "updated_at": "2024-01-01T00:00:00Z",
        "message": "Context updated successfully"
    }


@router.delete("/{context_id}", response_model=dict)
async def delete_context(
    context_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除上下文"""
    # TODO: 实现上下文删除逻辑
    return {
        "id": context_id,
        "message": "Context deleted successfully"
    }
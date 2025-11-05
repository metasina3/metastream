"""
Approval management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import Approval, User, Video, Channel
from datetime import datetime

router = APIRouter(prefix="/api/admin/approvals", tags=["approvals"])


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """Require admin role"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user


@router.get("/")
async def list_pending_approvals(
    type: str = None,  # 'video' | 'channel'
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    List pending approvals
    """
    query = db.query(Approval).filter(Approval.status == "pending")
    
    if type:
        query = query.filter(Approval.type == type)
    
    approvals = query.all()
    
    result = []
    for approval in approvals:
        entity_data = {}
        if approval.type == "video":
            entity = db.query(Video).filter(Video.id == approval.entity_id).first()
            if entity:
                entity_data = {"id": entity.id, "title": entity.title, "status": entity.status}
        elif approval.type == "channel":
            entity = db.query(Channel).filter(Channel.id == approval.entity_id).first()
            if entity:
                entity_data = {"id": entity.id, "name": entity.name, "slug": entity.slug}
        
        result.append({
            "id": approval.id,
            "type": approval.type,
            "entity_id": approval.entity_id,
            "entity_data": entity_data,
            "requested_at": approval.requested_at.isoformat()
        })
    
    return {"pending": result}


@router.post("/{approval_id}/approve")
async def approve(
    approval_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Approve an item
    """
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Update entity status
    if approval.type == "video":
        video = db.query(Video).filter(Video.id == approval.entity_id).first()
        if video:
            video.status = "approved"
            video.approved_by = admin.id
            video.approved_at = datetime.utcnow()
    elif approval.type == "channel":
        channel = db.query(Channel).filter(Channel.id == approval.entity_id).first()
        if channel:
            channel.status = "approved"
            channel.approved_by = admin.id
            channel.approved_at = datetime.utcnow()
    
    # Update approval
    approval.status = "approved"
    approval.approved_at = datetime.utcnow()
    approval.approved_by = admin.id
    
    db.commit()
    
    return {"success": True}


@router.post("/{approval_id}/reject")
async def reject(
    approval_id: int,
    reason: str = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Reject an item
    """
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Update entity status
    if approval.type == "video":
        video = db.query(Video).filter(Video.id == approval.entity_id).first()
        if video:
            video.status = "rejected"
    elif approval.type == "channel":
        channel = db.query(Channel).filter(Channel.id == approval.entity_id).first()
        if channel:
            channel.status = "rejected"
    
    # Update approval
    approval.status = "rejected"
    approval.reason = reason
    
    db.commit()
    
    return {"success": True}


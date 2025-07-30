"""
Admin Routes

This module provides admin endpoints for managing the application,
including scheduler control and manual job triggering.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import List, Dict, Any

from app.core.scheduler import task_scheduler

router = APIRouter()

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get the current status of the task scheduler."""
    jobs = task_scheduler.get_jobs()
    
    return {
        "scheduler_running": task_scheduler.scheduler.running,
        "current_time": datetime.utcnow().isoformat(),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }

@router.post("/scheduler/trigger-conversation-names")
async def trigger_conversation_name_generation():
    """
    Manually trigger the conversation name generation job.
    
    This is useful for testing or when you want to immediately process
    conversations without waiting for the scheduled time.
    """
    try:
        await task_scheduler.trigger_name_generation_now()
        return {
            "message": "Conversation name generation job triggered successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger conversation name generation: {str(e)}"
        )

@router.get("/scheduler/jobs")
async def list_scheduled_jobs():
    """List all scheduled jobs with detailed information."""
    jobs = task_scheduler.get_jobs()
    
    return {
        "total_jobs": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "func": job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "max_instances": job.max_instances,
                "misfire_grace_time": job.misfire_grace_time,
                "coalesce": job.coalesce
            }
            for job in jobs
        ]
    }

@router.post("/conversation-names/process-all")
async def process_all_conversations():
    """
    Process all conversations that need name generation.
    
    This endpoint provides the same functionality as the scheduled job
    but can be triggered manually for testing or immediate processing.
    """
    if not task_scheduler.conversation_name_generator:
        raise HTTPException(
            status_code=503,
            detail="Conversation name generator not initialized"
        )
    
    try:
        # Get conversations that need processing
        conversations = await task_scheduler.conversation_name_generator.find_conversations_needing_names()
        
        if not conversations:
            return {
                "message": "No conversations found that need name updates",
                "processed": 0,
                "total": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Process each conversation
        success_count = 0
        total_count = len(conversations)
        processed_conversations = []
        
        for conversation in conversations:
            try:
                success = await task_scheduler.conversation_name_generator.process_conversation(conversation)
                if success:
                    success_count += 1
                
                processed_conversations.append({
                    "conversation_id": conversation["_id"],
                    "current_name": conversation.get("name", ""),
                    "message_count": conversation.get("message_count", 0),
                    "success": success
                })
                
            except Exception as e:
                processed_conversations.append({
                    "conversation_id": conversation.get("_id", "unknown"),
                    "current_name": conversation.get("name", ""),
                    "message_count": conversation.get("message_count", 0),
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "message": f"Processed {total_count} conversations",
            "processed": success_count,
            "total": total_count,
            "success_rate": f"{(success_count/total_count)*100:.1f}%" if total_count > 0 else "0%",
            "conversations": processed_conversations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process conversations: {str(e)}"
        ) 
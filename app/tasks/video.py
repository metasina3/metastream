"""
Celery tasks for video processing
"""
from celery import shared_task
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.models import Video
from app.models.approval import Approval
from app.utils.datetime_utils import now_tehran
import subprocess
import os
from datetime import datetime

@shared_task(queue='prep')
def prepare_video(video_id: int):
    """
    Smart video processing with minimal re-encoding.
    Only re-encodes what's necessary for RTMP streaming.
    Uses only 2 CPU cores to avoid affecting live streams.
    """
    import json
    
    db: Session = SessionLocal()
    video = None
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {"success": False, "error": "Video not found"}
        
        # Update status to processing
        video.status = "processing"
        video.processing_progress = 10
        db.commit()
        
        # Input and output paths
        input_file = video.original_file
        if not input_file or not os.path.exists(input_file):
            video.status = "failed"
            db.commit()
            return {"success": False, "error": "Input file not found"}
        
        output_file = os.path.join(
            settings.UPLOAD_DIR,
            f"processed_{video_id}.mp4"
        )
        
        print(f"[VIDEO] Analyzing video {video_id} with ffprobe...")
        
        # Step 1: Analyze video with ffprobe
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            input_file
        ]
        
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        if probe_result.returncode != 0:
            print(f"[VIDEO] ffprobe failed: {probe_result.stderr}")
            video.status = "failed"
            db.commit()
            return {"success": False, "error": "Could not analyze video"}
        
        probe_data = json.loads(probe_result.stdout)
        
        # Find video and audio streams
        video_stream = None
        audio_stream = None
        
        for stream in probe_data.get('streams', []):
            if stream['codec_type'] == 'video' and not video_stream:
                video_stream = stream
            elif stream['codec_type'] == 'audio' and not audio_stream:
                audio_stream = stream
        
        # Step 2: Determine what needs encoding
        # RTMP compatible: h264 (video) + aac/mp3 (audio)
        video_codec = video_stream.get('codec_name', '') if video_stream else ''
        audio_codec = audio_stream.get('codec_name', '') if audio_stream else ''
        
        video_needs_encode = video_codec not in ['h264', 'avc']
        audio_needs_encode = audio_codec not in ['aac', 'mp3']
        
        print(f"[VIDEO] Video codec: {video_codec} → Encode: {video_needs_encode}")
        print(f"[VIDEO] Audio codec: {audio_codec} → Encode: {audio_needs_encode}")
        
        # Step 3: Build optimized FFmpeg command
        cmd = ["ffmpeg", "-i", input_file]
        
        # Video processing
        if video_needs_encode:
            print(f"[VIDEO] Re-encoding video stream...")
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",  # Fast encoding
                "-crf", "23",
                "-profile:v", "high",
                "-level", "4.0",
                "-threads", "2",  # Only 2 CPU cores
            ])
        else:
            print(f"[VIDEO] Copying video stream (no re-encode)⚡")
            cmd.extend(["-c:v", "copy"])
        
        # Audio processing
        if audio_needs_encode:
            print(f"[VIDEO] Re-encoding audio stream...")
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
            ])
        else:
            print(f"[VIDEO] Copying audio stream (no re-encode)⚡")
            cmd.extend(["-c:a", "copy"])
        
        # RTMP streaming flags
        cmd.extend([
            "-movflags", "+faststart",
            "-max_muxing_queue_size", "1024",
            "-y",
            output_file
        ])
        
        print(f"[VIDEO] Processing (2 cores max)...")
        
        # Execute FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            print(f"[VIDEO] FFmpeg failed: {result.stderr}")
            video.status = "failed"
            db.commit()
            return {"success": False, "error": result.stderr}
        
        print(f"[VIDEO] Processing completed!")
        
        # Get duration from probe data
        try:
            duration = float(probe_data.get('format', {}).get('duration', 0))
            video.duration = int(duration)
            print(f"[VIDEO] Duration: {video.duration}s")
        except:
            video.duration = 0
        
        # Delete original file to save storage
        if os.path.exists(input_file):
            try:
                os.remove(input_file)
                print(f"[VIDEO] Deleted original file")
            except Exception as e:
                print(f"[VIDEO] Warning: Could not delete original: {e}")
        
            # Update video record
            video.processed_file = output_file
            video.status = "awaiting_approval"
            video.processing_progress = 100
            video.processed_at = now_tehran()
            db.commit()

            # Create approval request
            try:
                a = Approval(
                    type="video",
                    entity_id=video.id,
                    user_id=video.user_id,
                    status="pending"
                )
                db.add(a)
                db.commit()
                db.refresh(a)
                print(f"[VIDEO] Approval request created")
                
                # Send Telegram notification
                try:
                    from app.utils.telegram import send_approval_notification
                    send_approval_notification(a.id, "video", video.id, db)
                except Exception as e:
                    print(f"[VIDEO] Telegram notification error: {e}")
            except Exception:
                db.rollback()
        
        return {"success": True, "video_id": video_id}
        
    except Exception as e:
        print(f"[VIDEO] Error: {e}")
        import traceback
        traceback.print_exc()
        if video:
            video.status = "failed"
            db.commit()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


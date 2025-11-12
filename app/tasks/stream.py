"""
Celery tasks for stream management
"""
from celery import shared_task
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import StreamSchedule, Channel, Video
from app.utils.datetime_utils import now_tehran, to_tehran
from datetime import timedelta
import subprocess
import os
import signal
import time

@shared_task(queue='stream')
def check_and_start_streams():
    """
    Periodic task to check scheduled streams and start them when time arrives.
    This should run every 30 seconds.
    Only checks streams that are still scheduled and haven't expired.
    """
    db: Session = SessionLocal()
    try:
        now = now_tehran()
        
        # Find streams that should start now (within last 5 minutes to catch missed ones)
        threshold = now - timedelta(minutes=5)
        max_future = now + timedelta(days=1)  # Don't process streams more than 1 day in future
        
        # Only get scheduled streams that haven't expired and are within reasonable range
        all_scheduled = db.query(StreamSchedule).filter(
            StreamSchedule.status == "scheduled",
            StreamSchedule.start_time <= max_future,
            StreamSchedule.start_time >= threshold  # Only recent missed or current streams
        ).all()
        
        print(f"[STREAM] Checking streams at {now}. Found {len(all_scheduled)} active scheduled streams")
        
        started_count = 0
        for stream in all_scheduled:
            start_t = to_tehran(stream.start_time)
            diff_seconds = (now - start_t).total_seconds()
            
            # Start if time has arrived (within 5 minutes tolerance)
            if start_t <= now:
                print(f"[STREAM] Starting stream {stream.id}: '{stream.title}' (time passed {diff_seconds:.0f}s ago)")
                start_stream_task.delay(stream.id)
                started_count += 1
            else:
                print(f"  Stream {stream.id}: '{stream.title}' - starts in {(-diff_seconds):.0f}s")
        
        return {"checked": len(all_scheduled), "started": started_count}
    finally:
        db.close()


@shared_task(queue='stream')
def start_stream_task(stream_id: int):
    """
    Start a specific stream by streaming the video to RTMP.
    """
    db: Session = SessionLocal()
    stream = None
    try:
        stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
        if not stream:
            print(f"[STREAM] Stream {stream_id} not found")
            return {"success": False, "error": "Stream not found"}
        
        # Only start if still scheduled (double-check to avoid race conditions)
        if stream.status != "scheduled":
            print(f"[STREAM] Stream {stream_id} is not scheduled (status: {stream.status}) - skipping")
            return {"success": False, "error": f"Stream status is {stream.status}"}
        
        # Verify start time hasn't expired too long ago (more than 10 minutes = cancel)
        stream_start = to_tehran(stream.start_time)
        now_check = now_tehran()
        time_passed = (now_check - stream_start).total_seconds()
        if time_passed > 600:  # 10 minutes
            print(f"[STREAM] Stream {stream_id} start time expired too long ago ({stream_start}, {time_passed:.0f}s ago) - cancelling")
            stream.status = "cancelled"
            db.commit()
            return {"success": False, "error": "Stream start time expired too long ago"}
        
        # Get channel
        channel = db.query(Channel).filter(Channel.id == stream.channel_id).first()
        if not channel or not channel.rtmp_url or not channel.rtmp_key:
            stream.status = "cancelled"
            db.commit()
            print(f"[STREAM] Channel {stream.channel_id} missing RTMP config")
            return {"success": False, "error": "Channel RTMP config missing"}
        
        # Get video
        video = db.query(Video).filter(Video.id == stream.video_id).first()
        if not video or video.status != "ready":
            stream.status = "cancelled"
            db.commit()
            print(f"[STREAM] Video {stream.video_id} not ready")
            return {"success": False, "error": "Video not ready"}
        
        # Use processed file if available, otherwise original
        video_file = video.processed_file if video.processed_file and os.path.exists(video.processed_file) else video.original_file
        if not video_file or not os.path.exists(video_file):
            stream.status = "cancelled"
            db.commit()
            print(f"[STREAM] Video file not found: {video_file}")
            return {"success": False, "error": "Video file not found"}
        
        # Build RTMP URL
        rtmp_destination = f"{channel.rtmp_url}/{channel.rtmp_key}" if not channel.rtmp_url.endswith('/') else f"{channel.rtmp_url}{channel.rtmp_key}"
        
        # Update status to live
        stream.status = "live"
        stream.started_at = now_tehran()
        db.commit()
        
        print(f"[STREAM] Starting RTMP stream: {video_file} -> {rtmp_destination}")
        
        # Find FFmpeg binary (try multiple common paths)
        # First try to use which/whereis, then try common paths
        ffmpeg_bin = None
        
        # Try using 'which' command first
        try:
            result = subprocess.run(["which", "ffmpeg"], capture_output=True, timeout=1, text=True)
            if result.returncode == 0 and result.stdout.strip():
                candidate = result.stdout.strip()
                # Verify it works
                test_result = subprocess.run([candidate, "-version"], capture_output=True, timeout=2)
                if test_result.returncode == 0:
                    ffmpeg_bin = candidate
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        
        # If which didn't work, try common paths
        if not ffmpeg_bin:
            ffmpeg_paths = ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]
            for path in ffmpeg_paths:
                if path == "ffmpeg":
                    # Try to execute directly
                    try:
                        result = subprocess.run([path, "-version"], capture_output=True, timeout=2)
                        if result.returncode == 0:
                            ffmpeg_bin = path
                            break
                    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                        continue
                elif os.path.exists(path):
                    try:
                        result = subprocess.run([path, "-version"], capture_output=True, timeout=2)
                        if result.returncode == 0:
                            ffmpeg_bin = path
                            break
                    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                        continue
        
        if not ffmpeg_bin:
            # Final attempt: try to install FFmpeg via apt-get (if we have root)
            try:
                print("[STREAM] FFmpeg not found, attempting to install...")
                install_result = subprocess.run(
                    ["apt-get", "update"],
                    capture_output=True,
                    timeout=30
                )
                if install_result.returncode == 0:
                    install_result = subprocess.run(
                        ["apt-get", "install", "-y", "--no-install-recommends", "ffmpeg"],
                        capture_output=True,
                        timeout=60
                    )
                    if install_result.returncode == 0:
                        # Try again after installation
                        result = subprocess.run(["which", "ffmpeg"], capture_output=True, timeout=2, text=True)
                        if result.returncode == 0:
                            ffmpeg_bin = result.stdout.strip()
            except Exception as install_error:
                print(f"[STREAM] Failed to auto-install FFmpeg: {install_error}")
        
        if not ffmpeg_bin:
            raise Exception("FFmpeg not found. Please install FFmpeg in the container: apt-get update && apt-get install -y ffmpeg")
        
        # Start FFmpeg RTMP streaming in background
        # Video is already prepared for RTMP, so we just copy streams without re-encoding
        ffmpeg_cmd = [
            ffmpeg_bin,
            "-re",  # Read input at native frame rate (important for live streaming)
            "-i", video_file,
            "-c:v", "copy",  # Copy video stream (no re-encoding)
            "-c:a", "copy",  # Copy audio stream (no re-encoding)
            "-f", "flv",
            "-rtmp_live", "live",
            rtmp_destination
        ]
        
        # Add proxy configuration if set
        # FFmpeg uses environment variables for proxy (http_proxy, https_proxy, HTTP_PROXY, HTTPS_PROXY)
        env = os.environ.copy()
        from app.core.config import settings
        # Check if proxy is set and not empty
        if settings.STREAM_PROXY and settings.STREAM_PROXY.strip():
            proxy_url = settings.STREAM_PROXY.strip()
            if proxy_url:
                # If proxy is on host machine (127.0.0.1 or localhost), use host.docker.internal
                # This allows container to access services on host
                if proxy_url.startswith("http://127.0.0.1") or proxy_url.startswith("http://localhost"):
                    # Replace 127.0.0.1 or localhost with host.docker.internal
                    proxy_url = proxy_url.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal")
                    print(f"[STREAM] 🔄 Proxy URL adjusted for Docker container: {proxy_url}")
                
                print(f"[STREAM] ✅ PROXY CONFIGURED: Using proxy for streaming: {proxy_url}")
                print(f"[STREAM] Setting http_proxy and https_proxy environment variables for FFmpeg")
                # Set proxy environment variables for FFmpeg
                env["http_proxy"] = proxy_url
                env["https_proxy"] = proxy_url
                env["HTTP_PROXY"] = proxy_url
                env["HTTPS_PROXY"] = proxy_url
                print(f"[STREAM] Environment variables set: http_proxy={proxy_url}, https_proxy={proxy_url}")
            else:
                print(f"[STREAM] ⚠️ STREAM_PROXY is set but empty, streaming without proxy")
        else:
            print(f"[STREAM] ℹ️ STREAM_PROXY not set, streaming without proxy")
        
        # Start FFmpeg process in background with environment variables
        # Use start_new_session=True instead of preexec_fn for better compatibility
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,  # Redirect to /dev/null to avoid filling logs
                stderr=subprocess.DEVNULL,
                env=env,  # Pass environment variables including proxy
                start_new_session=True  # Create new process group
            )
        except AttributeError:
            # Fallback for older Python versions
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,  # Pass environment variables including proxy
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
        
        print(f"[STREAM] FFmpeg started with PID {process.pid} for stream {stream_id}")
        if settings.STREAM_PROXY and settings.STREAM_PROXY.strip():
            print(f"[STREAM] ✅ FFmpeg is using proxy: {proxy_url}")
            print(f"[STREAM] Environment variables passed to FFmpeg:")
            print(f"[STREAM]   - http_proxy={env.get('http_proxy')}")
            print(f"[STREAM]   - https_proxy={env.get('https_proxy')}")
            print(f"[STREAM]   - HTTP_PROXY={env.get('HTTP_PROXY')}")
            print(f"[STREAM]   - HTTPS_PROXY={env.get('HTTPS_PROXY')}")
        else:
            print(f"[STREAM] ⚠️ FFmpeg is NOT using proxy (STREAM_PROXY not set)")
        
        # Store PID in Redis for later cleanup/kill
        try:
            import redis
            redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            pid_key = f"stream:pid:{stream_id}"
            redis_client.setex(pid_key, 3600 * 24, str(process.pid))  # Store for 24 hours
            print(f"[STREAM] Stored PID {process.pid} in Redis with key: {pid_key}")
        except Exception as redis_error:
            print(f"[STREAM] Warning: Could not store PID in Redis: {redis_error}")
        
        return {"success": True, "stream_id": stream_id, "pid": process.pid}
        
    except Exception as e:
        error_msg = str(e)
        print(f"[STREAM] Error starting stream {stream_id}: {error_msg}")
        if stream:
            try:
                stream.status = "cancelled"
                stream.error_message = error_msg  # Store error message
                db.commit()
            except Exception as db_error:
                print(f"[STREAM] Error updating stream status: {db_error}")
        return {"success": False, "error": error_msg}
    finally:
        db.close()


@shared_task(queue='stream')
def monitor_stream_workers():
    """
    Monitor stream worker status and log statistics.
    This helps track autoscaler performance and system load.
    Runs every 60 seconds.
    """
    db: Session = SessionLocal()
    try:
        now = now_tehran()
        
        # Count active streams
        scheduled_count = db.query(StreamSchedule).filter(
            StreamSchedule.status == "scheduled"
        ).count()
        
        live_count = db.query(StreamSchedule).filter(
            StreamSchedule.status == "live"
        ).count()
        
        total_active = scheduled_count + live_count
        
        # Get queue length from Redis
        try:
            import redis
            redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            queue_length = redis_client.llen('celery')  # Approximate queue length
        except Exception:
            queue_length = 0
        
        print(f"[MONITOR] Active streams: {total_active} (scheduled: {scheduled_count}, live: {live_count})")
        print(f"[MONITOR] Queue length: {queue_length}")
        print(f"[MONITOR] Autoscaler will adjust workers based on queue length and active streams")
        
        return {
            "scheduled": scheduled_count,
            "live": live_count,
            "total_active": total_active,
            "queue_length": queue_length
        }
    finally:
        db.close()


@shared_task(queue='stream')
def check_live_streams():
    """
    Periodic task to check live streams and mark them as ended when duration expires.
    This should run every 60 seconds.
    Also auto-cancels old scheduled streams that never started (expired more than 1 hour ago).
    """
    db: Session = SessionLocal()
    try:
        now = now_tehran()
        
        # Find live streams that should have ended based on duration
        live_streams = db.query(StreamSchedule).filter(
            StreamSchedule.status == "live"
        ).all()
        
        ended_count = 0
        for stream in live_streams:
            if stream.started_at and stream.duration:
                # Calculate when stream should end
                expected_end = to_tehran(stream.started_at) + timedelta(seconds=stream.duration)
                
                # Add 10 seconds buffer for completion
                if now >= expected_end + timedelta(seconds=10):
                    stream.status = "ended"
                    stream.ended_at = now
                    ended_count += 1
                    print(f"[STREAM] Stream {stream.id} ended (duration expired)")
        
        # Auto-cancel old scheduled streams that never started (more than 1 hour past start time)
        expired_threshold = now - timedelta(hours=1)
        expired_streams = db.query(StreamSchedule).filter(
            StreamSchedule.status == "scheduled",
            StreamSchedule.start_time < expired_threshold
        ).all()
        
        cancelled_count = 0
        for stream in expired_streams:
            stream.status = "cancelled"
            cancelled_count += 1
            print(f"[STREAM] Auto-cancelled expired stream {stream.id}: '{stream.title}' (start_time was {to_tehran(stream.start_time)})")
        
        if ended_count > 0 or cancelled_count > 0:
            db.commit()
            if ended_count > 0:
                print(f"[STREAM] Marked {ended_count} streams as ended")
            if cancelled_count > 0:
                print(f"[STREAM] Auto-cancelled {cancelled_count} expired streams")
        
        return {"checked": len(live_streams), "ended": ended_count, "cancelled": cancelled_count}
    except Exception as e:
        print(f"[STREAM] Error checking live streams: {e}")
        return {"error": str(e)}
    finally:
        db.close()


@shared_task(queue='stream')
def stop_stream(stream_id: int):
    """
    Stop a running stream.
    """
    db: Session = SessionLocal()
    try:
        stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
        if not stream:
            return {"success": False, "error": "Stream not found"}
        
        if stream.status == "live":
            stream.status = "ended"
            stream.ended_at = now_tehran()
            db.commit()
            print(f"[STREAM] Stream {stream_id} stopped manually")
            return {"success": True}
        else:
            return {"success": False, "error": f"Stream is not live (status: {stream.status})"}
    finally:
        db.close()


@shared_task(queue='stream')
def kill_stream_process(stream_id: int):
    """
    Kill FFmpeg process for a specific stream.
    This runs in the stream worker container where FFmpeg processes are running.
    """
    try:
        import redis
        import signal
        import os
        import time
        
        redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        pid_key = f"stream:pid:{stream_id}"
        pid_str = redis_client.get(pid_key)
        
        if pid_str:
            pid = int(pid_str)
            print(f"[STREAM] Killing FFmpeg process {pid} for stream {stream_id}...")
            
            try:
                # Try to kill the process group (FFmpeg and its children)
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)
                    print(f"[STREAM] Sent SIGTERM to process group {pgid} (PID {pid})")
                except ProcessLookupError:
                    print(f"[STREAM] Process {pid} not found (may have already terminated)")
                    redis_client.delete(pid_key)
                    return {"success": True, "message": "Process already terminated"}
                except OSError as e:
                    # If getpgid fails, try killing the process directly
                    print(f"[STREAM] Could not get process group, trying direct kill: {e}")
                    try:
                        os.kill(pid, signal.SIGTERM)
                        print(f"[STREAM] Sent SIGTERM to process {pid}")
                    except ProcessLookupError:
                        print(f"[STREAM] Process {pid} not found")
                        redis_client.delete(pid_key)
                        return {"success": True, "message": "Process already terminated"}
                
                # Wait a bit, then force kill if still alive
                time.sleep(2)
                
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGKILL)
                    print(f"[STREAM] Sent SIGKILL to process group {pgid}")
                except ProcessLookupError:
                    print(f"[STREAM] Process {pid} already terminated")
                except OSError:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"[STREAM] Sent SIGKILL to process {pid}")
                    except ProcessLookupError:
                        print(f"[STREAM] Process {pid} already terminated")
                
                # Cleanup zombie processes by waiting for them
                # This prevents zombie processes from accumulating
                try:
                    # Wait for the process to fully terminate (non-blocking)
                    # This reaps the zombie process
                    os.waitpid(pid, os.WNOHANG)
                    # Also try to wait for any child processes in the process group
                    try:
                        os.waitpid(-pgid, os.WNOHANG)
                    except (OSError, ProcessLookupError):
                        pass
                except (OSError, ProcessLookupError, ChildProcessError):
                    # Process already reaped or not a child of this process
                    pass
                
            except Exception as kill_error:
                print(f"[STREAM] Error killing process {pid}: {kill_error}")
            
            # Remove PID from Redis
            redis_client.delete(pid_key)
            print(f"[STREAM] Removed PID from Redis")
            return {"success": True, "message": f"Process {pid} killed successfully"}
        else:
            print(f"[STREAM] No PID found in Redis for stream {stream_id}")
            return {"success": False, "message": "No PID found in Redis"}
            
    except Exception as e:
        print(f"[STREAM] Error in kill_stream_process: {e}")
        return {"success": False, "error": str(e)}


@shared_task(queue='stream')
def update_max_viewers():
    """
    Periodic task to update max_viewers in database from Redis.
    Redis handles real-time calculations and caching.
    This task periodically saves the maximum viewer count to database.
    Runs every 2 minutes.
    """
    db: Session = SessionLocal()
    try:
        import redis
        redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        
        # Get all live streams
        live_streams = db.query(StreamSchedule).filter(
            StreamSchedule.status == "live"
        ).all()
        
        if not live_streams:
            return {"updated": 0, "checked": 0}
        
        updated_count = 0
        for stream in live_streams:
            try:
                # Get online count from Redis (same key used by Go service)
                online_key = f"online:{stream.id}"
                online_count = redis_client.scard(online_key)
                
                # Update max_viewers if current count is higher
                if online_count > stream.max_viewers:
                    old_max = stream.max_viewers
                    stream.max_viewers = online_count
                    updated_count += 1
                    print(f"[VIEWERS] Stream {stream.id} ({stream.title}): Updated max_viewers from {old_max} to {online_count}")
            
            except Exception as e:
                print(f"[VIEWERS] Error updating max_viewers for stream {stream.id}: {e}")
                continue
        
        if updated_count > 0:
            db.commit()
            print(f"[VIEWERS] Updated max_viewers for {updated_count} streams")
        
        return {
            "updated": updated_count,
            "checked": len(live_streams)
        }
    
    except Exception as e:
        print(f"[VIEWERS] Error in update_max_viewers task: {e}")
        return {"error": str(e), "updated": 0, "checked": 0}
    finally:
        db.close()


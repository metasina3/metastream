"""
Celery tasks for stream management
"""
from celery import shared_task
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import StreamSchedule, Channel, Video
from app.utils.datetime_utils import now_tehran, to_tehran
from app.utils.ffmpeg import get_video_duration
from datetime import timedelta
import subprocess
import os
import signal
import time
import logging
from logging.handlers import RotatingFileHandler

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


def _setup_stream_logger(stream_id: int):
    """
    Setup a dedicated logger for a specific stream.
    Creates log file at logs/streams/stream_{stream_id}.log
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "streams")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create logger
    logger_name = f"aparat_stream_{stream_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Create file handler
    log_file = os.path.join(logs_dir, f"stream_{stream_id}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger


@shared_task(bind=True, queue='stream')
def start_stream_task(self, stream_id: int):
    """
    Start a specific stream by streaming the video to RTMP with resume capability.
    This task will automatically retry from the last position if RTMP connection is lost.
    """
    # Setup logger for this stream
    logger = _setup_stream_logger(stream_id)
    task_id = self.request.id if hasattr(self, 'request') else None
    
    db: Session = SessionLocal()
    stream = None
    try:
        stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
        if not stream:
            logger.error(f"Stream {stream_id} not found (task_id: {task_id})")
            return {"success": False, "error": "Stream not found"}
        
        # Only start if still scheduled (double-check to avoid race conditions)
        if stream.status != "scheduled":
            logger.warning(f"Stream {stream_id} is not scheduled (status: {stream.status}) - skipping (task_id: {task_id})")
            return {"success": False, "error": f"Stream status is {stream.status}"}
        
        # Verify start time hasn't expired too long ago (more than 10 minutes = cancel)
        stream_start = to_tehran(stream.start_time)
        now_check = now_tehran()
        time_passed = (now_check - stream_start).total_seconds()
        if time_passed > 600:  # 10 minutes
            logger.warning(f"Stream {stream_id} start time expired too long ago ({stream_start}, {time_passed:.0f}s ago) - cancelling (task_id: {task_id})")
            stream.status = "cancelled"
            db.commit()
            return {"success": False, "error": "Stream start time expired too long ago"}
        
        # Get channel
        channel = db.query(Channel).filter(Channel.id == stream.channel_id).first()
        if not channel or not channel.rtmp_url or not channel.rtmp_key:
            stream.status = "cancelled"
            db.commit()
            logger.error(f"Channel {stream.channel_id} missing RTMP config (task_id: {task_id})")
            return {"success": False, "error": "Channel RTMP config missing"}
        
        # Get video
        video = db.query(Video).filter(Video.id == stream.video_id).first()
        if not video or video.status != "ready":
            stream.status = "cancelled"
            db.commit()
            logger.error(f"Video {stream.video_id} not ready (task_id: {task_id})")
            return {"success": False, "error": "Video not ready"}
        
        # Use processed file if available, otherwise original
        video_file = video.processed_file if video.processed_file and os.path.exists(video.processed_file) else video.original_file
        if not video_file or not os.path.exists(video_file):
            stream.status = "cancelled"
            db.commit()
            logger.error(f"Video file not found: {video_file} (task_id: {task_id})")
            return {"success": False, "error": "Video file not found"}
        
        # Build RTMP URL
        rtmp_destination = f"{channel.rtmp_url}/{channel.rtmp_key}" if not channel.rtmp_url.endswith('/') else f"{channel.rtmp_url}{channel.rtmp_key}"
        
        # Mask stream key for logging (show only last 4 chars)
        stream_key_masked = channel.rtmp_key[:4] + "****" if len(channel.rtmp_key) > 4 else "****"
        
        # Get video duration
        video_duration = get_video_duration(video_file)
        if video_duration <= 0:
            logger.error(f"Could not get video duration for {video_file} (task_id: {task_id})")
            stream.status = "cancelled"
            db.commit()
            return {"success": False, "error": "Could not determine video duration"}
        
        # Update status to live
        stream.status = "live"
        stream.started_at = now_tehran()
        db.commit()
        
        # Log stream start
        logger.info(f"=== STREAM START ===")
        logger.info(f"Stream ID: {stream_id}")
        logger.info(f"Task ID: {task_id}")
        logger.info(f"Video file: {video_file}")
        logger.info(f"RTMP destination: {channel.rtmp_url}/{stream_key_masked}")
        logger.info(f"Video duration: {video_duration:.2f} seconds")
        logger.info(f"Initial offset: 0.00 seconds")
        
        # Find FFmpeg binary (try multiple common paths)
        ffmpeg_bin = None
        
        # Try using 'which' command first
        try:
            result = subprocess.run(["which", "ffmpeg"], capture_output=True, timeout=1, text=True)
            if result.returncode == 0 and result.stdout.strip():
                candidate = result.stdout.strip()
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
            raise Exception("FFmpeg not found. Please install FFmpeg in the container: apt-get update && apt-get install -y ffmpeg")
        
        # Resume mechanism: track offset and retry on failure
        offset_seconds = 0.0
        attempt = 0
        total_attempts = 0
        max_retry_delay = 30  # Maximum seconds to wait before retry
        
        # Store PID in Redis for later cleanup/kill
        import redis
        redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        pid_key = f"stream:pid:{stream_id}"
        
        while offset_seconds < video_duration:
            attempt += 1
            total_attempts += 1
            
            # Check if stream was cancelled
            db.refresh(stream)
            if stream.status != "live":
                logger.info(f"Stream {stream_id} status changed to {stream.status}, stopping (task_id: {task_id})")
                break
            
            # Log attempt start
            logger.info(f"--- ATTEMPT #{attempt} ---")
            logger.info(f"Offset: {offset_seconds:.2f} seconds ({offset_seconds/video_duration*100:.1f}% of video)")
            logger.info(f"Remaining: {video_duration - offset_seconds:.2f} seconds")
            
            # Build FFmpeg command with resume support
            ffmpeg_cmd = [
                ffmpeg_bin,
                "-re",  # Read input at native frame rate
                "-ss", str(offset_seconds),  # Seek to offset position
                "-i", video_file,
                "-c:v", "copy",  # Copy video stream (no re-encoding)
                "-c:a", "copy",  # Copy audio stream (no re-encoding)
                "-f", "flv",
                "-rtmp_live", "live",
                "-rw_timeout", "5000000",  # 5 seconds timeout for RTMP write operations (in microseconds)
                rtmp_destination
            ]
            
            # Log command (masked)
            cmd_str = " ".join(ffmpeg_cmd)
            cmd_str_masked = cmd_str.replace(channel.rtmp_key, stream_key_masked)
            logger.info(f"FFmpeg command: {cmd_str_masked}")
            
            # Record start time
            start_ts = time.time()
            
            # Start FFmpeg process
            try:
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            except AttributeError:
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
            
            logger.info(f"FFmpeg started with PID {process.pid}")
            
            # Store PID in Redis
            try:
                redis_client.setex(pid_key, 3600 * 24, str(process.pid))
            except Exception as redis_error:
                logger.warning(f"Could not store PID in Redis: {redis_error}")
            
            # Wait for process to complete with timeout monitoring
            # Use polling instead of communicate() to detect stuck/stopped processes
            try:
                import threading
                import queue
                
                # Collect stderr in background with timeout
                stderr_queue = queue.Queue()
                stderr_data = []
                
                def read_stderr():
                    try:
                        while True:
                            try:
                                chunk = process.stderr.read(1024)
                                if not chunk:
                                    break
                                stderr_queue.put(chunk)
                            except:
                                break
                    except:
                        pass
                    finally:
                        stderr_queue.put(None)  # Signal end
                
                stderr_thread = threading.Thread(target=read_stderr, daemon=True)
                stderr_thread.start()
                
                # Poll process with timeout detection
                process_start_time = time.time()
                max_idle_time = 20  # If process runs for more than expected without output, consider it stuck
                check_interval = 2  # Check every 2 seconds
                last_stderr_time = time.time()
                
                while process.poll() is None:
                    current_time = time.time()
                    elapsed = current_time - process_start_time
                    
                    # Check if stream was cancelled
                    db.refresh(stream)
                    if stream.status != "live":
                        logger.info(f"Stream {stream_id} status changed to {stream.status}, terminating FFmpeg")
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except:
                            process.kill()
                        break
                    
                    # Collect stderr chunks (non-blocking)
                    try:
                        while True:
                            chunk = stderr_queue.get_nowait()
                            if chunk is None:
                                break
                            stderr_data.append(chunk)
                            last_stderr_time = current_time
                    except queue.Empty:
                        pass
                    
                    # Check for stuck process
                    # Only kill if process is actually stopped (SIGSTOP) or truly stuck
                    # Don't rely on stderr alone - FFmpeg may not output much during normal streaming
                    try:
                        import psutil
                        proc = psutil.Process(process.pid)
                        status = proc.status()
                        
                        # Only kill if process is explicitly stopped (SIGSTOP)
                        # This is the main case we want to handle
                        if status == psutil.STATUS_STOPPED:
                            logger.warning(f"FFmpeg process is stopped (SIGSTOP detected, status: {status}), killing and retrying")
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except:
                                process.kill()
                            exit_code = -1
                            break
                        
                        # For other cases, be very conservative
                        # Only kill if process is zombie or truly dead
                        if status == psutil.STATUS_ZOMBIE:
                            logger.warning(f"FFmpeg process is zombie, killing and retrying")
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except:
                                process.kill()
                            exit_code = -1
                            break
                            
                    except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        # If psutil fails, don't kill - just log
                        # We don't want to kill healthy processes
                        if isinstance(e, psutil.NoSuchProcess):
                            # Process already dead
                            break
                        # For other errors, continue - don't kill
                        pass
                    
                    time.sleep(check_interval)
                
                # Process has exited or was killed
                exit_code = process.returncode
                end_ts = time.time()
                run_duration = end_ts - start_ts
                
                # Collect remaining stderr
                try:
                    while True:
                        chunk = stderr_queue.get_nowait()
                        if chunk is None:
                            break
                        stderr_data.append(chunk)
                except queue.Empty:
                    pass
                
                stderr_str = b''.join(stderr_data).decode('utf-8', errors='ignore') if stderr_data else ""
                
                # Update offset based on actual run time
                # Since we're using -re (realtime), the time elapsed should match the video time played
                offset_seconds += run_duration
                
                logger.info(f"FFmpeg exited with code {exit_code}")
                logger.info(f"Run duration: {run_duration:.2f} seconds")
                logger.info(f"New offset: {offset_seconds:.2f} seconds")
                
                # Check if we've completed the video
                if offset_seconds >= video_duration:
                    logger.info(f"=== STREAM COMPLETED SUCCESSFULLY ===")
                    logger.info(f"Total duration: {video_duration:.2f} seconds")
                    logger.info(f"Total attempts: {total_attempts}")
                    stream.status = "ended"
                    stream.ended_at = now_tehran()
                    db.commit()
                    redis_client.delete(pid_key)
                    return {"success": True, "stream_id": stream_id, "completed": True, "total_attempts": total_attempts}
                
                # If exit code is 0, stream completed normally (shouldn't happen if offset < duration)
                if exit_code == 0:
                    logger.info(f"FFmpeg exited normally, but offset ({offset_seconds:.2f}) < duration ({video_duration:.2f})")
                    logger.info("This may indicate the video ended prematurely or there was an issue")
                    # Continue to next attempt
                
                # If exit code is non-zero or process was killed, log error and retry
                if exit_code != 0:
                    logger.error(f"FFmpeg failed with exit code {exit_code}")
                    if stderr_str:
                        logger.error(f"Stderr: {stderr_str[:500]}")  # Log first 500 chars
                    
                    # Check for specific error patterns
                    if stderr_str:
                        error_lower = stderr_str.lower()
                        if any(keyword in error_lower for keyword in ['broken pipe', 'connection reset', 'connection refused', 'timeout', 'network', 'rtmp']):
                            logger.error(f"Network/RTMP error detected: {stderr_str[:200]}")
                        else:
                            logger.error(f"Unknown error: {stderr_str[:200]}")
                    else:
                        logger.error("No stderr output (process may have been killed or stopped)")
                    
                    # Wait before retry (exponential backoff, max 30 seconds)
                    retry_delay = min(2 ** min(attempt - 1, 4), max_retry_delay)
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                
            except Exception as e:
                logger.exception(f"Exception while running FFmpeg (attempt #{attempt}): {e}")
                # Try to kill the process if it's still running
                try:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                    except:
                        pass
                
                # Wait before retry
                retry_delay = min(2 ** min(attempt - 1, 4), max_retry_delay)
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
        
        # If we exit the loop without completing
        logger.warning(f"Stream {stream_id} ended without completing (offset: {offset_seconds:.2f}, duration: {video_duration:.2f})")
        stream.status = "ended"
        stream.ended_at = now_tehran()
        db.commit()
        redis_client.delete(pid_key)
        
        return {"success": True, "stream_id": stream_id, "completed": False, "total_attempts": total_attempts}
        
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error starting stream {stream_id} (task_id: {task_id}): {error_msg}")
        if stream:
            try:
                stream.status = "cancelled"
                stream.error_message = error_msg
                db.commit()
            except Exception as db_error:
                logger.exception(f"Error updating stream status: {db_error}")
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


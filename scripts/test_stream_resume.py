#!/usr/bin/env python3
"""
Test script for stream resume functionality.
This script will:
1. Find a live stream
2. Wait 2 minutes after stream start
3. Simulate network disconnection by blocking RTMP connection
4. Wait 15 seconds
5. Restore connection
6. Monitor logs and generate report
"""

import sys
import os
import time
import signal
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models import StreamSchedule, Channel
from app.utils.datetime_utils import now_tehran, to_tehran
import redis

def get_live_streams():
    """Get all live streams"""
    db = SessionLocal()
    try:
        streams = db.query(StreamSchedule).filter(
            StreamSchedule.status == "live"
        ).all()
        return streams
    finally:
        db.close()

def get_stream_info(stream_id):
    """Get stream information including RTMP URL"""
    db = SessionLocal()
    try:
        stream = db.query(StreamSchedule).filter(StreamSchedule.id == stream_id).first()
        if not stream:
            return None
        
        channel = db.query(Channel).filter(Channel.id == stream.channel_id).first()
        if not channel:
            return None
        
        return {
            "stream_id": stream.id,
            "title": stream.title,
            "started_at": to_tehran(stream.started_at) if stream.started_at else None,
            "rtmp_url": channel.rtmp_url,
            "rtmp_key": channel.rtmp_key,
            "aparat_username": channel.aparat_username
        }
    finally:
        db.close()

def get_ffmpeg_pid(stream_id):
    """Get FFmpeg PID from Redis"""
    try:
        redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        pid_key = f"stream:pid:{stream_id}"
        pid_str = redis_client.get(pid_key)
        if pid_str:
            return int(pid_str)
        return None
    except Exception as e:
        print(f"Error getting PID from Redis: {e}")
        return None

def extract_host_from_rtmp(rtmp_url):
    """Extract hostname/IP from RTMP URL"""
    # rtmp://example.com:1935/app/stream
    match = re.match(r'rtmp://([^:/]+)', rtmp_url)
    if match:
        return match.group(1)
    return None

def block_rtmp_connection(host):
    """Block RTMP connection using iptables"""
    try:
        # Block outgoing connections to RTMP host on port 1935
        cmd = ["iptables", "-A", "OUTPUT", "-d", host, "-p", "tcp", "--dport", "1935", "-j", "DROP"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Blocked RTMP connection to {host}")
            return True
        else:
            print(f"❌ Failed to block connection: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error blocking connection: {e}")
        return False

def unblock_rtmp_connection(host):
    """Unblock RTMP connection"""
    try:
        # Remove the blocking rule
        cmd = ["iptables", "-D", "OUTPUT", "-d", host, "-p", "tcp", "--dport", "1935", "-j", "DROP"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Unblocked RTMP connection to {host}")
            return True
        else:
            # Try to flush if rule doesn't exist
            print(f"⚠️ Rule may not exist, trying alternative method...")
            return True
    except Exception as e:
        print(f"❌ Error unblocking connection: {e}")
        return False

def pause_ffmpeg_process(pid):
    """Pause FFmpeg process using SIGSTOP"""
    try:
        os.kill(pid, signal.SIGSTOP)
        print(f"✅ Paused FFmpeg process {pid} (SIGSTOP)")
        return True
    except ProcessLookupError:
        print(f"⚠️ Process {pid} not found")
        return False
    except Exception as e:
        print(f"❌ Error pausing process: {e}")
        return False

def resume_ffmpeg_process(pid):
    """Resume FFmpeg process using SIGCONT"""
    try:
        os.kill(pid, signal.SIGCONT)
        print(f"✅ Resumed FFmpeg process {pid} (SIGCONT)")
        return True
    except ProcessLookupError:
        print(f"⚠️ Process {pid} not found")
        return False
    except Exception as e:
        print(f"❌ Error resuming process: {e}")
        return False

def read_log_file(stream_id):
    """Read stream log file"""
    # Try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent / "logs" / "streams" / f"stream_{stream_id}.log",
        Path("/app") / "logs" / "streams" / f"stream_{stream_id}.log",
        Path("/root/metastream") / "logs" / "streams" / f"stream_{stream_id}.log",
    ]
    
    for log_file in possible_paths:
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
                continue
    
    # If not found, try to find it
    print(f"Tried paths:")
    for p in possible_paths:
        print(f"  - {p} (exists: {p.exists()})")
    return None

def analyze_logs(log_content, test_start_time, test_end_time):
    """Analyze logs for resume behavior"""
    if not log_content:
        return {"error": "No log content"}
    
    lines = log_content.split('\n')
    
    # Find test period
    test_lines = []
    for line in lines:
        # Extract timestamp from log line
        # Format: 2025-11-13 18:00:00 - INFO - message
        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if match:
            try:
                log_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                if test_start_time <= log_time <= test_end_time:
                    test_lines.append(line)
            except:
                pass
    
    # Analyze
    attempts = []
    errors = []
    retries = []
    
    current_attempt = None
    for line in test_lines:
        if "ATTEMPT #" in line:
            match = re.search(r'ATTEMPT #(\d+)', line)
            if match:
                current_attempt = int(match.group(1))
                attempts.append(current_attempt)
        elif "FFmpeg failed" in line or "ERROR" in line:
            errors.append(line)
        elif "Retrying" in line:
            retries.append(line)
        elif "Network/RTMP error" in line:
            errors.append(line)
    
    return {
        "total_attempts_during_test": len(attempts),
        "errors": errors,
        "retries": retries,
        "test_lines": test_lines[-20:]  # Last 20 lines
    }

def main():
    print("=" * 60)
    print("STREAM RESUME TEST SCRIPT")
    print("=" * 60)
    print()
    
    # Step 1: Find live stream (wait if needed)
    print("📡 Step 1: Finding live streams...")
    max_wait = 300  # Wait up to 5 minutes for stream to start
    wait_interval = 5
    waited = 0
    
    streams = get_live_streams()
    while not streams and waited < max_wait:
        print(f"   No live streams yet, waiting... ({waited}s/{max_wait}s)")
        time.sleep(wait_interval)
        waited += wait_interval
        streams = get_live_streams()
    
    if not streams:
        print("❌ No live streams found after waiting. Please start a stream first.")
        return 1
    
    print(f"✅ Found {len(streams)} live stream(s)")
    for s in streams:
        print(f"   - Stream ID: {s.id}, Title: {s.title}")
    
    # Use first stream
    stream_id = streams[0].id
    print(f"\n🎯 Using stream ID: {stream_id}")
    
    # Get stream info
    stream_info = get_stream_info(stream_id)
    if not stream_info:
        print("❌ Could not get stream information")
        return 1
    
    print(f"   Title: {stream_info['title']}")
    print(f"   Started at: {stream_info['started_at']}")
    print(f"   RTMP URL: {stream_info['rtmp_url']}")
    print(f"   Aparat: {stream_info['aparat_username']}")
    
    # Get PID
    pid = get_ffmpeg_pid(stream_id)
    if not pid:
        print("❌ Could not get FFmpeg PID from Redis")
        return 1
    
    print(f"   FFmpeg PID: {pid}")
    
    # Calculate wait time (2 minutes after start)
    if not stream_info['started_at']:
        print("❌ Stream has no started_at timestamp")
        return 1
    
    now = now_tehran()
    elapsed = (now - stream_info['started_at']).total_seconds()
    wait_time = max(0, 120 - elapsed)  # Wait until 2 minutes after start
    
    print(f"\n⏱️  Step 2: Waiting {wait_time:.1f} seconds until 2 minutes after stream start...")
    if wait_time > 0:
        time.sleep(wait_time)
    
    print(f"✅ Ready to test (elapsed: {(now_tehran() - stream_info['started_at']).total_seconds():.1f}s)")
    
    # Extract host from RTMP URL
    host = extract_host_from_rtmp(stream_info['rtmp_url'])
    if not host:
        print("❌ Could not extract host from RTMP URL")
        return 1
    
    print(f"   RTMP Host: {host}")
    
    # Step 3: Block connection (simulate network failure)
    test_start_time = now_tehran()
    print(f"\n🔴 Step 3: Simulating network disconnection at {test_start_time}...")
    print("   Using SIGSTOP to pause FFmpeg process (simulates network failure)")
    
    # Use SIGSTOP to pause the process (simulates network failure)
    blocked = pause_ffmpeg_process(pid)
    
    if not blocked:
        print("❌ Failed to simulate disconnection")
        return 1
    
    # Step 4: Wait 15 seconds
    disconnect_duration = 15
    print(f"\n⏳ Step 4: Waiting {disconnect_duration} seconds with connection blocked...")
    time.sleep(disconnect_duration)
    
    # Step 5: Restore connection
    test_end_time = now_tehran()
    print(f"\n🟢 Step 5: Restoring connection at {test_end_time}...")
    print("   Using SIGCONT to resume FFmpeg process")
    
    resume_ffmpeg_process(pid)
    
    # Step 6: Wait a bit for resume to happen
    print(f"\n⏳ Step 6: Waiting 30 seconds for resume to complete...")
    time.sleep(30)
    
    # Step 7: Analyze logs
    print(f"\n📊 Step 7: Analyzing logs...")
    log_content = read_log_file(stream_id)
    
    if log_content:
        analysis = analyze_logs(log_content, test_start_time, test_end_time)
        
        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)
        print(f"Stream ID: {stream_id}")
        print(f"Test Start: {test_start_time}")
        print(f"Test End: {test_end_time}")
        print(f"Disconnect Duration: {disconnect_duration} seconds")
        print()
        print(f"Attempts during test: {analysis.get('total_attempts_during_test', 0)}")
        print(f"Errors found: {len(analysis.get('errors', []))}")
        print(f"Retries found: {len(analysis.get('retries', []))}")
        print()
        
        if analysis.get('errors'):
            print("Errors:")
            for error in analysis['errors'][:5]:  # Show first 5
                print(f"  - {error[:100]}")
        
        if analysis.get('retries'):
            print("\nRetries:")
            for retry in analysis['retries']:
                print(f"  - {retry}")
        
        print("\nLast log lines during test:")
        for line in analysis.get('test_lines', [])[-10:]:
            print(f"  {line}")
        
        # Check if resume worked
        if analysis.get('retries'):
            print("\n✅ RESUME MECHANISM WORKED! Retries detected.")
        else:
            print("\n⚠️  No retries detected. Resume may not have triggered.")
    else:
        print("❌ Could not read log file")
        print(f"   Expected: logs/streams/stream_{stream_id}.log")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


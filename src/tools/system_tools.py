"""
System Tools
============

Tools for system operations, command execution, and resource monitoring.
"""

import os
import sys
import subprocess
import platform
import psutil
import json
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from google.genai import types


def run_command(
    command: str,
    shell: bool = True,
    timeout: Optional[int] = 60,
    working_dir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
    check: bool = False
) -> Dict[str, Any]:
    """
    Execute a system command with safety features.
    
    Args:
        command: Command to execute
        shell: Whether to use shell execution
        timeout: Command timeout in seconds
        working_dir: Working directory for command execution
        env: Environment variables
        capture_output: Whether to capture command output
        check: Whether to raise exception on non-zero exit code
    
    Returns:
        Dictionary with command result
    """
    try:
        # Prepare environment
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)
        
        # Execute command
        result = subprocess.run(
            command,
            shell=shell,
            timeout=timeout,
            cwd=working_dir,
            env=cmd_env,
            capture_output=capture_output,
            text=True,
            check=check
        )
        
        return {
            "success": result.returncode == 0,
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout if capture_output else None,
            "stderr": result.stderr if capture_output else None,
            "working_dir": working_dir or os.getcwd()
        }
    
    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout} seconds",
            "command": command,
            "timeout": timeout
        }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"Command failed with exit code {e.returncode}",
            "command": command,
            "exit_code": e.returncode,
            "stdout": e.stdout if capture_output else None,
            "stderr": e.stderr if capture_output else None
        }
    except Exception as e:
        return {
            "error": f"Failed to execute command: {str(e)}",
            "command": command
        }


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information.
    
    Returns:
        Dictionary with system information
    """
    try:
        # Basic system info
        info = {
            "platform": {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
        }
        
        # CPU information
        info["cpu"] = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=1),
            "frequency": {
                "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                "min": psutil.cpu_freq().min if psutil.cpu_freq() else None,
                "max": psutil.cpu_freq().max if psutil.cpu_freq() else None
            }
        }
        
        # Memory information
        memory = psutil.virtual_memory()
        info["memory"] = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
            "total_human": _format_bytes(memory.total),
            "available_human": _format_bytes(memory.available),
            "used_human": _format_bytes(memory.used)
        }
        
        # Disk information
        disk = psutil.disk_usage('/')
        info["disk"] = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "total_human": _format_bytes(disk.total),
            "used_human": _format_bytes(disk.used),
            "free_human": _format_bytes(disk.free)
        }
        
        # Network information
        net_io = psutil.net_io_counters()
        info["network"] = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_received": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_received": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout
        }
        
        # Process information
        info["processes"] = {
            "total": len(psutil.pids()),
            "running": len([p for p in psutil.process_iter(['status']) if p.info['status'] == psutil.STATUS_RUNNING])
        }
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        info["boot_time"] = boot_time.isoformat()
        info["uptime_seconds"] = (datetime.now() - boot_time).total_seconds()
        
        return info
    
    except Exception as e:
        return {"error": f"Failed to get system info: {str(e)}"}


def monitor_resources(
    duration: int = 5,
    interval: float = 1.0
) -> Dict[str, Any]:
    """
    Monitor system resources over a period of time.
    
    Args:
        duration: Monitoring duration in seconds
        interval: Sampling interval in seconds
    
    Returns:
        Dictionary with resource usage statistics
    """
    try:
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            sample = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                "network_io": psutil.net_io_counters()._asdict()
            }
            samples.append(sample)
            time.sleep(interval)
        
        # Calculate statistics
        cpu_values = [s["cpu_percent"] for s in samples]
        memory_values = [s["memory_percent"] for s in samples]
        
        return {
            "duration": duration,
            "samples_count": len(samples),
            "statistics": {
                "cpu": {
                    "min": min(cpu_values),
                    "max": max(cpu_values),
                    "average": sum(cpu_values) / len(cpu_values)
                },
                "memory": {
                    "min": min(memory_values),
                    "max": max(memory_values),
                    "average": sum(memory_values) / len(memory_values)
                }
            },
            "samples": samples
        }
    
    except Exception as e:
        return {"error": f"Failed to monitor resources: {str(e)}"}


def manage_processes(
    action: str,
    process_name: Optional[str] = None,
    pid: Optional[int] = None,
    signal_type: str = "TERM"
) -> Dict[str, Any]:
    """
    Manage system processes.
    
    Args:
        action: Action to perform (list, kill, info, find)
        process_name: Process name to search for
        pid: Process ID
        signal_type: Signal type for kill action (TERM, KILL, INT)
    
    Returns:
        Dictionary with operation result
    """
    try:
        if action == "list":
            # List all processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "action": "list",
                "count": len(processes),
                "processes": processes[:50]  # Limit to 50 processes
            }
        
        elif action == "find":
            # Find processes by name
            if not process_name:
                return {"error": "Process name required for find action"}
            
            matching = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        matching.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "action": "find",
                "search_term": process_name,
                "count": len(matching),
                "processes": matching
            }
        
        elif action == "info":
            # Get detailed info about a process
            if not pid:
                return {"error": "PID required for info action"}
            
            try:
                proc = psutil.Process(pid)
                info = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "status": proc.status(),
                    "username": proc.username(),
                    "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "memory_info": proc.memory_info()._asdict(),
                    "num_threads": proc.num_threads(),
                    "cmdline": ' '.join(proc.cmdline()),
                    "cwd": proc.cwd(),
                    "connections": len(proc.connections())
                }
                
                return {
                    "action": "info",
                    "process": info
                }
            except psutil.NoSuchProcess:
                return {"error": f"No process with PID {pid}"}
        
        elif action == "kill":
            # Kill a process
            if not pid:
                return {"error": "PID required for kill action"}
            
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                
                # Map signal types
                signal_map = {
                    "TERM": signal.SIGTERM,
                    "KILL": signal.SIGKILL,
                    "INT": signal.SIGINT
                }
                
                sig = signal_map.get(signal_type.upper(), signal.SIGTERM)
                proc.send_signal(sig)
                
                # Wait a bit and check if process is gone
                time.sleep(0.5)
                if not proc.is_running():
                    return {
                        "action": "kill",
                        "success": True,
                        "pid": pid,
                        "name": proc_name,
                        "signal": signal_type
                    }
                else:
                    return {
                        "action": "kill",
                        "success": False,
                        "pid": pid,
                        "name": proc_name,
                        "message": "Process still running after signal"
                    }
            
            except psutil.NoSuchProcess:
                return {"error": f"No process with PID {pid}"}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"error": f"Process management failed: {str(e)}"}


def schedule_task(
    command: str,
    schedule_type: str,
    schedule_time: Optional[str] = None,
    cron_expression: Optional[str] = None
) -> Dict[str, Any]:
    """
    Schedule a task for later execution.
    
    Args:
        command: Command to schedule
        schedule_type: Type of schedule (once, cron, at)
        schedule_time: Time for one-time execution
        cron_expression: Cron expression for recurring tasks
    
    Returns:
        Dictionary with scheduling result
    """
    try:
        system = platform.system()
        
        if system == "Darwin" or system == "Linux":
            if schedule_type == "at":
                # Use 'at' command for one-time scheduling
                if not schedule_time:
                    return {"error": "Schedule time required for 'at' scheduling"}
                
                proc = subprocess.run(
                    f"echo '{command}' | at {schedule_time}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                return {
                    "scheduled": proc.returncode == 0,
                    "type": "at",
                    "command": command,
                    "time": schedule_time,
                    "output": proc.stdout,
                    "error": proc.stderr if proc.returncode != 0 else None
                }
            
            elif schedule_type == "cron":
                # Add to crontab for recurring tasks
                if not cron_expression:
                    return {"error": "Cron expression required for cron scheduling"}
                
                # Get current crontab
                proc = subprocess.run(
                    "crontab -l",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                current_cron = proc.stdout if proc.returncode == 0 else ""
                
                # Add new entry
                new_entry = f"{cron_expression} {command}"
                new_cron = current_cron + "\n" + new_entry
                
                # Update crontab
                proc = subprocess.run(
                    f"echo '{new_cron}' | crontab -",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                return {
                    "scheduled": proc.returncode == 0,
                    "type": "cron",
                    "command": command,
                    "cron_expression": cron_expression,
                    "entry": new_entry,
                    "error": proc.stderr if proc.returncode != 0 else None
                }
        
        elif system == "Windows":
            # Use Task Scheduler for Windows
            return {
                "error": "Windows Task Scheduler integration not yet implemented",
                "suggestion": "Use 'schtasks' command manually"
            }
        
        else:
            return {"error": f"Unsupported system: {system}"}
    
    except Exception as e:
        return {"error": f"Failed to schedule task: {str(e)}"}


def _format_bytes(bytes_value: int) -> str:
    """Format bytes in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


# Schema definitions for Gemini function calling
schema_run_command = types.FunctionDeclaration(
    name="run_command",
    description="Execute a system command",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to execute"},
            "working_dir": {"type": "string", "description": "Working directory for command execution"},
            "timeout": {"type": "integer", "description": "Command timeout in seconds"},
        },
        "required": ["command"]
    }
)

schema_get_system_info = types.FunctionDeclaration(
    name="get_system_info",
    description="Get comprehensive system information",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)

schema_manage_processes = types.FunctionDeclaration(
    name="manage_processes",
    description="Manage system processes (list, find, info, kill)",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "find", "info", "kill"], "description": "Action to perform"},
            "process_name": {"type": "string", "description": "Process name for find action"},
            "pid": {"type": "integer", "description": "Process ID for info/kill actions"},
            "signal_type": {"type": "string", "enum": ["TERM", "KILL", "INT"], "description": "Signal type for kill action"},
        },
        "required": ["action"]
    }
)

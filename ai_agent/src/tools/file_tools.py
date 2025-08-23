'''
File Manipulation Tools
=======================

Comprehensive file operations with safety checks and error handling.
'''

import os
import shutil
import json
import yaml
# import toml  # Commented out to remove toml dependency
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import hashlib
import mimetypes
from google.genai import types


def read_file(
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    max_size: Optional[int] = 10 * 1024 * 1024  # 10MB default
) -> Dict[str, Any]:
    """
    Read file contents with safety checks.

    Args:
        file_path: Path to the file
        encoding: File encoding
        max_size: Maximum file size to read (in bytes)

    Returns:
        Dictionary with file content and metadata
    """
    path = Path(file_path)
    print(f"Reading file: {file_path}")
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    if not path.is_file():
        return {"error": f"Not a file: {file_path}"}

    file_size = path.stat().st_size
    if max_size and file_size > max_size:
        return {
            "error": f"File too large: {file_size} bytes (max: {max_size} bytes)",
            "file_size": file_size
        }

    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()

        return {
            "content": content,
            "file_path": str(path.absolute()),
            "file_size": file_size,
            "encoding": encoding,
            "lines": len(content.splitlines()),
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        }
    except UnicodeDecodeError:
        # Try reading as binary
        with open(path, 'rb') as f:
            content = f.read()
        return {
            "content": content.hex(),
            "file_path": str(path.absolute()),
            "file_size": file_size,
            "encoding": "binary",
            "format": "hex"
        }
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


def write_file(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_dirs: bool = True,
    backup: bool = True
) -> Dict[str, Any]:
    """
    Write content to a file with safety features.

    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding
        create_dirs: Create parent directories if they don't exist
        backup: Create backup of existing file

    Returns:
        Dictionary with operation result
    """
    path = Path(file_path)
    print(f"Writing file: {file_path}")
    try:
        # Create parent directories if needed
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing file if requested
        backup_path = None
        if backup and path.exists():
            backup_path = path.with_suffix(path.suffix + '.bak')
            shutil.copy2(path, backup_path)

        # Write the file
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)

        return {
            "success": True,
            "file_path": str(path.absolute()),
            "bytes_written": len(content.encode(encoding)),
            "backup_path": str(backup_path) if backup_path else None
        }
    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}


def create_file(
    file_path: Union[str, Path],
    content: str = "",
    template: Optional[str] = None,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Create a new file with optional template.

    Args:
        file_path: Path to the new file
        content: Initial content
        template: Template name for file creation
        overwrite: Whether to overwrite existing file

    Returns:
        Dictionary with operation result
    """
    path = Path(file_path)

    if path.exists() and not overwrite:
        return {"error": f"File already exists: {file_path}"}

    # Apply template if specified
    # if template:
    #     content = _apply_template(template, path.suffix, content)

    return write_file(path, content, backup=False)


def delete_file(
    file_path: Union[str, Path],
    safe_delete: bool = True
) -> Dict[str, Any]:
    """
    Delete a file with safety checks.

    Args:
        file_path: Path to the file
        safe_delete: Move to trash instead of permanent deletion

    Returns:
        Dictionary with operation result
    """
    path = Path(file_path)

    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        if safe_delete:
            # Move to trash directory
            trash_dir = Path.home() / ".ai_agent" / "trash"
            trash_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_path = trash_dir / f"{timestamp}_{path.name}"
            shutil.move(str(path), str(trash_path))

            return {
                "success": True,
                "deleted": str(path),
                "moved_to": str(trash_path)
            }
        else:
            path.unlink()
            return {
                "success": True,
                "deleted": str(path)
            }
    except Exception as e:
        return {"error": f"Failed to delete file: {str(e)}"}


def move_file(
    source: Union[str, Path],
    destination: Union[str, Path],
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Move a file to a new location.

    Args:
        source: Source file path
        destination: Destination path
        overwrite: Whether to overwrite existing file

    Returns:
        Dictionary with operation result
    """
    src_path = Path(source)
    dst_path = Path(destination)

    if not src_path.exists():
        return {"error": f"Source file not found: {source}"}

    if dst_path.exists() and not overwrite:
        return {"error": f"Destination already exists: {destination}"}

    try:
        # Ensure destination directory exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src_path), str(dst_path))

        return {
            "success": True,
            "source": str(src_path),
            "destination": str(dst_path.absolute())
        }
    except Exception as e:
        return {"error": f"Failed to move file: {str(e)}"}


def copy_file(
    source: Union[str, Path],
    destination: Union[str, Path],
    overwrite: bool = False,
    preserve_metadata: bool = True
) -> Dict[str, Any]:
    """
    Copy a file to a new location.

    Args:
        source: Source file path
        destination: Destination path
        overwrite: Whether to overwrite existing file
        preserve_metadata: Preserve file metadata

    Returns:
        Dictionary with operation result
    """
    src_path = Path(source)
    dst_path = Path(destination)

    if not src_path.exists():
        return {"error": f"Source file not found: {source}"}

    if dst_path.exists() and not overwrite:
        return {"error": f"Destination already exists: {destination}"}

    try:
        # Ensure destination directory exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        if preserve_metadata:
            shutil.copy2(str(src_path), str(dst_path))
        else:
            shutil.copy(str(src_path), str(dst_path))

        return {
            "success": True,
            "source": str(src_path),
            "destination": str(dst_path.absolute())
        }
    except Exception as e:
        return {"error": f"Failed to copy file: {str(e)}"}


def list_files(
    directory: Union[str, Path] = ".",
    pattern: str = "*",
    recursive: bool = False,
    include_hidden: bool = False,
    file_type: Optional[str] = None,
    sort_by: str = "name",
    limit: int = 100
) -> Dict[str, Any]:
    """
    List files in a directory with filtering options.

    Args:
        directory: Directory path
        pattern: File pattern to match
        recursive: Search recursively
        include_hidden: Include hidden files
        file_type: Filter by file type (file, dir, link)
        sort_by: Sort criteria (name, size, modified)
        limit: Maximum number of files to return

    Returns:
        Dictionary with file list and metadata
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        return {"error": f"Directory not found: {directory}"}

    if not dir_path.is_dir():
        return {"error": f"Not a directory: {directory}"}

    try:
        # Get files based on pattern
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))

        # Filter hidden files
        if not include_hidden:
            files = [f for f in files if not f.name.startswith('.')]

        # Filter by type
        if file_type == "file":
            files = [f for f in files if f.is_file()]
        elif file_type == "dir":
            files = [f for f in files if f.is_dir()]
        elif file_type == "link":
            files = [f for f in files if f.is_symlink()]

        # Sort files
        if sort_by == "size":
            files.sort(key=lambda f: f.stat().st_size if f.exists() else 0, reverse=True)
        elif sort_by == "modified":
            files.sort(key=lambda f: f.stat().st_mtime if f.exists() else 0, reverse=True)
        else:  # name
            files.sort(key=lambda f: f.name)

        # Limit results
        files = files[:limit]

        # Prepare file information
        file_list = []
        for file_path in files:
            try:
                stat = file_path.stat()
                file_info = {
                    "name": file_path.name,
                    "path": str(file_path.absolute()),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "file" if file_path.is_file() else "dir" if file_path.is_dir() else "link",
                    "mime_type": mimetypes.guess_type(file_path)[0] or "unknown"
                }
                file_list.append(file_info)
            except OSError as e:
                # Handle potential permission issues or broken links
                print(f"Error accessing file {file_path}: {e}")
                continue

        return {
            "files": file_list,
            "count": len(file_list),
            "directory": str(dir_path.absolute()),
            "pattern": pattern,
            "recursive": recursive,
            "include_hidden": include_hidden,
            "file_type": file_type,
            "sort_by": sort_by,
            "limit": limit
        }
    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}"}


def search_files(directory: str = ".", pattern: str = "*") -> Dict[str, Any]:
    """
    Searches for files in a directory matching a given pattern.

    Args:
        directory: The directory to search in.
        pattern: The file pattern to search for.

    Returns:
        A dictionary containing the list of files found.
    """
    return list_files(directory=directory, pattern=pattern)

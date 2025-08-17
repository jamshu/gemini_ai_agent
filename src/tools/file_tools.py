"""
File Manipulation Tools
=======================

Comprehensive file operations with safety checks and error handling.
"""

import os
import shutil
import json
import yaml
import toml
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
    if template:
        content = _apply_template(template, path.suffix, content)
    
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
                    "path": str(file_path.relative_to(dir_path)),
                    "absolute_path": str(file_path.absolute()),
                    "type": "dir" if file_path.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:]
                }
                file_list.append(file_info)
            except Exception:
                continue
        
        return {
            "directory": str(dir_path.absolute()),
            "pattern": pattern,
            "count": len(file_list),
            "files": file_list,
            "recursive": recursive
        }
    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}"}


def search_files(
    directory: Union[str, Path] = ".",
    content_pattern: Optional[str] = None,
    name_pattern: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Search for files based on content or name patterns.
    
    Args:
        directory: Directory to search in
        content_pattern: Pattern to search in file contents
        name_pattern: Pattern to match file names
        extensions: List of file extensions to search
        max_results: Maximum number of results
    
    Returns:
        Dictionary with search results
    """
    dir_path = Path(directory)
    results = []
    
    if not dir_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    try:
        # Determine files to search
        if extensions:
            files = []
            for ext in extensions:
                files.extend(dir_path.rglob(f"*.{ext}"))
        else:
            files = dir_path.rglob(name_pattern or "*")
        
        for file_path in files:
            if len(results) >= max_results:
                break
            
            if not file_path.is_file():
                continue
            
            # Skip large files
            if file_path.stat().st_size > 1024 * 1024:  # 1MB
                continue
            
            try:
                # Search in content if pattern provided
                if content_pattern:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content_pattern.lower() in content.lower():
                            # Find matching lines
                            matching_lines = []
                            for i, line in enumerate(content.splitlines(), 1):
                                if content_pattern.lower() in line.lower():
                                    matching_lines.append({
                                        "line_number": i,
                                        "content": line.strip()
                                    })
                            
                            results.append({
                                "file": str(file_path.relative_to(dir_path)),
                                "absolute_path": str(file_path.absolute()),
                                "matches": matching_lines[:5]  # Limit matches per file
                            })
                elif name_pattern and name_pattern.lower() in file_path.name.lower():
                    results.append({
                        "file": str(file_path.relative_to(dir_path)),
                        "absolute_path": str(file_path.absolute())
                    })
            except Exception:
                continue
        
        return {
            "directory": str(dir_path.absolute()),
            "content_pattern": content_pattern,
            "name_pattern": name_pattern,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get detailed information about a file.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Dictionary with file information
    """
    path = Path(file_path)
    
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    
    try:
        stat = path.stat()
        
        # Calculate file hash for regular files
        file_hash = None
        if path.is_file() and stat.st_size < 100 * 1024 * 1024:  # 100MB
            try:
                with open(path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                pass
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        
        info = {
            "name": path.name,
            "path": str(path.absolute()),
            "type": "directory" if path.is_dir() else "file" if path.is_file() else "other",
            "size": stat.st_size,
            "size_human": _format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "owner_uid": stat.st_uid,
            "group_gid": stat.st_gid,
            "mime_type": mime_type,
            "extension": path.suffix,
            "sha256": file_hash
        }
        
        # Add line count for text files
        if path.is_file() and mime_type and mime_type.startswith('text'):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    info["lines"] = sum(1 for _ in f)
            except Exception:
                pass
        
        return info
    except Exception as e:
        return {"error": f"Failed to get file info: {str(e)}"}


def _apply_template(template: str, extension: str, content: str) -> str:
    """Apply a template based on file type."""
    templates = {
        "python": '''"""
{description}
"""

def main():
    {content}
    pass

if __name__ == "__main__":
    main()
''',
        "javascript": '''/**
 * {description}
 */

function main() {
    {content}
}

main();
''',
        "html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{description}</title>
</head>
<body>
    {content}
</body>
</html>
''',
        "markdown": '''# {description}

{content}

## References

- 
'''
    }
    
    # Map extensions to templates
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".html": "html",
        ".md": "markdown"
    }
    
    template_name = ext_map.get(extension, None)
    if template_name and template_name in templates:
        return templates[template_name].format(
            description=content or "New file",
            content=content
        )
    
    return content


def _format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


# Schema definitions for Gemini function calling
schema_read_file = types.FunctionDeclaration(
    name="read_file",
    description="Read the contents of a file",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the file to read"},
            "encoding": {"type": "string", "description": "File encoding (default: utf-8)"},
        },
        "required": ["file_path"]
    }
)

schema_write_file = types.FunctionDeclaration(
    name="write_file",
    description="Write content to a file",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Content to write to the file"},
            "create_dirs": {"type": "boolean", "description": "Create parent directories if needed"},
            "backup": {"type": "boolean", "description": "Create backup of existing file"},
        },
        "required": ["file_path", "content"]
    }
)

schema_list_files = types.FunctionDeclaration(
    name="list_files",
    description="List files in a directory",
    parameters={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Directory path"},
            "pattern": {"type": "string", "description": "File pattern to match"},
            "recursive": {"type": "boolean", "description": "Search recursively"},
            "file_type": {"type": "string", "enum": ["file", "dir", "link"], "description": "Filter by file type"},
        },
        "required": []
    }
)

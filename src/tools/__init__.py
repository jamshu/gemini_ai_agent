"""
Enhanced Tool System for AI Agent
==================================

Provides a comprehensive set of tools for file manipulation, code analysis,
project management, testing, and more.
"""

from .file_tools import (
    read_file,
    write_file,
    create_file,
    delete_file,
    move_file,
    copy_file,
    list_files,
    search_files,
    get_file_info
)

from .code_tools import (
    analyze_code,
    format_code,
    lint_code,
    find_dependencies,
    generate_documentation,
    refactor_code,
    find_code_patterns
)

from .project_tools import (
    create_project,
    init_git_repo,
    run_tests,
    build_project,
    install_dependencies,
    create_virtual_env,
    manage_packages
)

from .system_tools import (
    run_command,
    get_system_info,
    monitor_resources,
    manage_processes,
    schedule_task
)

from .ai_tools import (
    summarize_text,
    explain_code,
    generate_code,
    translate_code,
    optimize_code,
    suggest_improvements
)

__all__ = [
    # File tools
    'read_file', 'write_file', 'create_file', 'delete_file',
    'move_file', 'copy_file', 'list_files', 'search_files', 'get_file_info',
    
    # Code tools
    'analyze_code', 'format_code', 'lint_code', 'find_dependencies',
    'generate_documentation', 'refactor_code', 'find_code_patterns',
    
    # Project tools
    'create_project', 'init_git_repo', 'run_tests', 'build_project',
    'install_dependencies', 'create_virtual_env', 'manage_packages',
    
    # System tools
    'run_command', 'get_system_info', 'monitor_resources',
    'manage_processes', 'schedule_task',
    
    # AI tools
    'summarize_text', 'explain_code', 'generate_code', 'translate_code',
    'optimize_code', 'suggest_improvements'
]

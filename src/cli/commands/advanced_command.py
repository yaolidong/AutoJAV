"""Advanced features CLI commands."""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional

from .base_command import BaseCommand
from ...utils.progress_persistence import get_progress_persistence
from ...utils.duplicate_detector import get_duplicate_detector, DuplicateStrategy
from ...utils.batch_processor import get_batch_processor, BatchMode, ScheduleType
from ...utils.performance_monitor import get_performance_monitor
from ...scanner.file_scanner import FileScanner
from ...models.video_file import VideoFile


class AdvancedCommand(BaseCommand):
    """Commands for advanced features like progress persistence, duplicate detection, etc."""
    
    @property
    def name(self) -> str:
        """Command name."""
        return "advanced"
    
    @property
    def description(self) -> str:
        """Command description."""
        return "Advanced features (progress persistence, duplicate detection, batch processing)"
    
    def __init__(self):
        super().__init__()
        self.progress_persistence = get_progress_persistence()
        self.duplicate_detector = get_duplicate_detector()
        self.batch_processor = get_batch_processor()
        self.performance_monitor = get_performance_monitor()
    
    def add_parser(self, subparsers):
        """Add command parser to subparsers."""
        parser = self._create_parser(subparsers)
        self.add_arguments(parser)
        return parser
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        subparsers = parser.add_subparsers(dest='advanced_action', help='Advanced feature actions')
        
        # Progress persistence commands
        progress_parser = subparsers.add_parser('progress', help='Progress persistence commands')
        progress_subparsers = progress_parser.add_subparsers(dest='progress_action')
        
        # List sessions
        list_sessions_parser = progress_subparsers.add_parser('list', help='List processing sessions')
        list_sessions_parser.add_argument('--include-completed', action='store_true',
                                        help='Include completed sessions')
        
        # Resume session
        resume_parser = progress_subparsers.add_parser('resume', help='Resume processing session')
        resume_parser.add_argument('session_id', help='Session ID to resume')
        
        # Session info
        info_parser = progress_subparsers.add_parser('info', help='Get session information')
        info_parser.add_argument('session_id', help='Session ID')
        
        # Delete session
        delete_parser = progress_subparsers.add_parser('delete', help='Delete session')
        delete_parser.add_argument('session_id', help='Session ID to delete')
        
        # Cleanup old sessions
        cleanup_parser = progress_subparsers.add_parser('cleanup', help='Cleanup old sessions')
        cleanup_parser.add_argument('--max-age-days', type=int, default=30,
                                  help='Maximum age in days for sessions to keep')
        
        # Duplicate detection commands
        duplicate_parser = subparsers.add_parser('duplicates', help='Duplicate detection commands')
        duplicate_subparsers = duplicate_parser.add_subparsers(dest='duplicate_action')
        
        # Scan for duplicates
        scan_parser = duplicate_subparsers.add_parser('scan', help='Scan for duplicate files')
        scan_parser.add_argument('directory', help='Directory to scan')
        scan_parser.add_argument('--recursive', action='store_true', help='Recursive scan')
        scan_parser.add_argument('--report-file', help='Save report to file')
        
        # Handle duplicates
        handle_parser = duplicate_subparsers.add_parser('handle', help='Handle duplicate files')
        handle_parser.add_argument('directory', help='Directory to scan')
        handle_parser.add_argument('--strategy', choices=['skip', 'keep_larger', 'keep_newer', 'keep_both'],
                                 default='skip', help='Duplicate handling strategy')
        handle_parser.add_argument('--dry-run', action='store_true', help='Dry run (no actual changes)')
        
        # Clear duplicate cache
        clear_cache_parser = duplicate_subparsers.add_parser('clear-cache', help='Clear duplicate detection cache')
        
        # Batch processing commands
        batch_parser = subparsers.add_parser('batch', help='Batch processing commands')
        batch_subparsers = batch_parser.add_subparsers(dest='batch_action')
        
        # Create batch job
        create_job_parser = batch_subparsers.add_parser('create-job', help='Create batch job')
        create_job_parser.add_argument('name', help='Job name')
        create_job_parser.add_argument('--source', action='append', required=True,
                                     help='Source directory (can be specified multiple times)')
        create_job_parser.add_argument('--target', required=True, help='Target directory')
        create_job_parser.add_argument('--mode', choices=['sequential', 'parallel', 'adaptive'],
                                     default='parallel', help='Processing mode')
        create_job_parser.add_argument('--max-concurrent', type=int, default=3,
                                     help='Maximum concurrent files')
        
        # List batch jobs
        list_jobs_parser = batch_subparsers.add_parser('list-jobs', help='List batch jobs')
        
        # Run batch job
        run_job_parser = batch_subparsers.add_parser('run-job', help='Run batch job')
        run_job_parser.add_argument('job_id', help='Job ID to run')
        run_job_parser.add_argument('--resume-session', help='Session ID to resume')
        
        # Schedule job
        schedule_parser = batch_subparsers.add_parser('schedule', help='Schedule batch job')
        schedule_parser.add_argument('job_id', help='Job ID to schedule')
        schedule_parser.add_argument('--type', choices=['interval', 'daily', 'weekly'],
                                   required=True, help='Schedule type')
        schedule_parser.add_argument('--interval-minutes', type=int, help='Interval in minutes')
        schedule_parser.add_argument('--hour', type=int, help='Hour (0-23)')
        schedule_parser.add_argument('--minute', type=int, default=0, help='Minute (0-59)')
        schedule_parser.add_argument('--weekday', type=int, help='Weekday (0=Monday, 6=Sunday)')
        
        # List scheduled tasks
        list_tasks_parser = batch_subparsers.add_parser('list-tasks', help='List scheduled tasks')
        
        # Start/stop scheduler
        start_scheduler_parser = batch_subparsers.add_parser('start-scheduler', help='Start task scheduler')
        stop_scheduler_parser = batch_subparsers.add_parser('stop-scheduler', help='Stop task scheduler')
        
        # Performance monitoring commands
        perf_parser = subparsers.add_parser('performance', help='Performance monitoring commands')
        perf_subparsers = perf_parser.add_subparsers(dest='perf_action')
        
        # Start monitoring
        start_monitor_parser = perf_subparsers.add_parser('start', help='Start performance monitoring')
        
        # Stop monitoring
        stop_monitor_parser = perf_subparsers.add_parser('stop', help='Stop performance monitoring')
        
        # Get status
        status_parser = perf_subparsers.add_parser('status', help='Get performance status')
        
        # Export report
        report_parser = perf_subparsers.add_parser('report', help='Export performance report')
        report_parser.add_argument('--output', help='Output file path')
        report_parser.add_argument('--include-raw', action='store_true', help='Include raw data')
        
        # Clear history
        clear_history_parser = perf_subparsers.add_parser('clear', help='Clear performance history')
    
    async def execute(self, args, app=None) -> Dict[str, Any]:
        """Execute the advanced command."""
        if args.advanced_action == 'progress':
            return await self._handle_progress_commands(args)
        elif args.advanced_action == 'duplicates':
            return await self._handle_duplicate_commands(args)
        elif args.advanced_action == 'batch':
            return await self._handle_batch_commands(args)
        elif args.advanced_action == 'performance':
            return await self._handle_performance_commands(args)
        else:
            return {'error': 'Unknown advanced action'}
    
    async def _handle_progress_commands(self, args) -> Dict[str, Any]:
        """Handle progress persistence commands."""
        if args.progress_action == 'list':
            sessions = self.progress_persistence.list_sessions(args.include_completed)
            return {
                'success': True,
                'sessions': sessions,
                'count': len(sessions)
            }
        
        elif args.progress_action == 'resume':
            session = self.progress_persistence.resume_session(args.session_id)
            if session:
                return {
                    'success': True,
                    'message': f'Resumed session {args.session_id}',
                    'session': session.to_dict()
                }
            else:
                return {
                    'success': False,
                    'error': f'Session {args.session_id} not found'
                }
        
        elif args.progress_action == 'info':
            progress = self.progress_persistence.get_session_progress(args.session_id)
            if progress:
                return {
                    'success': True,
                    'progress': progress
                }
            else:
                return {
                    'success': False,
                    'error': f'Session {args.session_id} not found'
                }
        
        elif args.progress_action == 'delete':
            success = self.progress_persistence.delete_session(args.session_id)
            return {
                'success': success,
                'message': f'Session {args.session_id} {"deleted" if success else "not found"}'
            }
        
        elif args.progress_action == 'cleanup':
            deleted_count = self.progress_persistence.cleanup_old_sessions(args.max_age_days)
            return {
                'success': True,
                'message': f'Cleaned up {deleted_count} old sessions',
                'deleted_count': deleted_count
            }
        
        return {'error': 'Unknown progress action'}
    
    async def _handle_duplicate_commands(self, args) -> Dict[str, Any]:
        """Handle duplicate detection commands."""
        if args.duplicate_action == 'scan':
            # Scan directory for video files
            scanner = FileScanner(
                source_directory=args.directory,
                recursive_scan=args.recursive
            )
            video_files = await asyncio.to_thread(scanner.scan_files)
            
            # Detect duplicates
            report = await self.duplicate_detector.detect_duplicates(video_files)
            
            result = {
                'success': True,
                'report': report.to_dict()
            }
            
            # Save report to file if requested
            if args.report_file:
                report_path = Path(args.report_file)
                with open(report_path, 'w') as f:
                    json.dump(result['report'], f, indent=2)
                result['report_file'] = str(report_path)
            
            return result
        
        elif args.duplicate_action == 'handle':
            # Scan and handle duplicates
            scanner = FileScanner(
                source_directory=args.directory,
                recursive_scan=True
            )
            video_files = await asyncio.to_thread(scanner.scan_files)
            
            # Detect duplicates
            report = await self.duplicate_detector.detect_duplicates(video_files)
            
            if not report.duplicate_groups:
                return {
                    'success': True,
                    'message': 'No duplicates found'
                }
            
            # Handle duplicates
            strategy = DuplicateStrategy(args.strategy)
            handle_result = await self.duplicate_detector.handle_duplicates(
                report.duplicate_groups,
                strategy,
                dry_run=args.dry_run
            )
            
            return {
                'success': True,
                'duplicate_report': report.to_dict(),
                'handle_result': handle_result,
                'dry_run': args.dry_run
            }
        
        elif args.duplicate_action == 'clear-cache':
            self.duplicate_detector.clear_cache()
            return {
                'success': True,
                'message': 'Duplicate detection cache cleared'
            }
        
        return {'error': 'Unknown duplicate action'}
    
    async def _handle_batch_commands(self, args) -> Dict[str, Any]:
        """Handle batch processing commands."""
        if args.batch_action == 'create-job':
            job = self.batch_processor.create_job(
                name=args.name,
                source_directories=args.source,
                target_directory=args.target,
                mode=BatchMode(args.mode),
                max_concurrent=args.max_concurrent
            )
            
            return {
                'success': True,
                'message': f'Created batch job: {job.name}',
                'job': job.to_dict()
            }
        
        elif args.batch_action == 'list-jobs':
            jobs = self.batch_processor.list_jobs()
            return {
                'success': True,
                'jobs': jobs,
                'count': len(jobs)
            }
        
        elif args.batch_action == 'run-job':
            try:
                result = await self.batch_processor.run_job(args.job_id, args.resume_session)
                return {
                    'success': True,
                    'result': result
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        elif args.batch_action == 'schedule':
            # Build schedule config
            schedule_config = {}
            
            if args.type == 'interval':
                if not args.interval_minutes:
                    return {'error': 'interval-minutes required for interval schedule'}
                schedule_config['interval_minutes'] = args.interval_minutes
            
            elif args.type == 'daily':
                if args.hour is None:
                    return {'error': 'hour required for daily schedule'}
                schedule_config['hour'] = args.hour
                schedule_config['minute'] = args.minute
            
            elif args.type == 'weekly':
                if args.hour is None or args.weekday is None:
                    return {'error': 'hour and weekday required for weekly schedule'}
                schedule_config['hour'] = args.hour
                schedule_config['minute'] = args.minute
                schedule_config['weekday'] = args.weekday
            
            try:
                task = self.batch_processor.schedule_job(
                    args.job_id,
                    ScheduleType(args.type),
                    schedule_config
                )
                
                return {
                    'success': True,
                    'message': f'Scheduled job {args.job_id}',
                    'task': task.to_dict()
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
        elif args.batch_action == 'list-tasks':
            tasks = self.batch_processor.list_scheduled_tasks()
            return {
                'success': True,
                'tasks': tasks,
                'count': len(tasks)
            }
        
        elif args.batch_action == 'start-scheduler':
            self.batch_processor.start_scheduler()
            return {
                'success': True,
                'message': 'Task scheduler started'
            }
        
        elif args.batch_action == 'stop-scheduler':
            self.batch_processor.stop_scheduler()
            return {
                'success': True,
                'message': 'Task scheduler stopped'
            }
        
        return {'error': 'Unknown batch action'}
    
    async def _handle_performance_commands(self, args) -> Dict[str, Any]:
        """Handle performance monitoring commands."""
        if args.perf_action == 'start':
            self.performance_monitor.start_monitoring()
            return {
                'success': True,
                'message': 'Performance monitoring started'
            }
        
        elif args.perf_action == 'stop':
            self.performance_monitor.stop_monitoring()
            return {
                'success': True,
                'message': 'Performance monitoring stopped'
            }
        
        elif args.perf_action == 'status':
            summary = self.performance_monitor.get_performance_summary()
            return {
                'success': True,
                'performance_summary': summary
            }
        
        elif args.perf_action == 'report':
            report = self.performance_monitor.export_performance_report(args.include_raw)
            
            result = {
                'success': True,
                'report': report
            }
            
            # Save to file if specified
            if args.output:
                output_path = Path(args.output)
                with open(output_path, 'w') as f:
                    json.dump(report, f, indent=2)
                result['output_file'] = str(output_path)
            
            return result
        
        elif args.perf_action == 'clear':
            self.performance_monitor.clear_history()
            return {
                'success': True,
                'message': 'Performance history cleared'
            }
        
        return {'error': 'Unknown performance action'}
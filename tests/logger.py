"""
Comprehensive logging system for Legal Agent System tests.
Provides detailed reporting of each test problem and interaction.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class TestLogEntry:
    """Detailed test log entry."""
    timestamp: str
    test_name: str
    stage_name: str
    status: str  # "PASSED", "FAILED", "SKIPPED", "ERROR"
    duration: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    azure_openai_interaction: Optional[Dict[str, Any]] = None

@dataclass
class StageLogEntry:
    """Stage log entry."""
    timestamp: str
    stage_name: str
    stage_description: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    duration: float
    test_results: List[TestLogEntry]

@dataclass
class SessionLogEntry:
    """Complete test session log entry."""
    session_id: str
    start_time: str
    end_time: str
    total_duration: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float
    stages: List[StageLogEntry]
    system_info: Dict[str, Any]
    configuration: Dict[str, Any]

class TestLogger:
    """Comprehensive test logger for detailed reporting."""
    
    def __init__(self, log_dir: str = "test_logs"):
        """Initialize the test logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create session ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Initialize session data
        self.session_start_time = datetime.now()
        self.stages: List[StageLogEntry] = []
        self.current_stage: Optional[StageLogEntry] = None
        self.current_tests: List[TestLogEntry] = []
        
        # Setup file logging
        self.setup_file_logging()
        
        # System information
        self.system_info = self._get_system_info()
        
    def setup_file_logging(self):
        """Setup file logging for detailed output."""
        # Main log file
        self.main_log_file = self.log_dir / f"test_session_{self.session_id}.log"
        
        # Detailed JSON log file
        self.json_log_file = self.log_dir / f"test_session_{self.session_id}.json"
        
        # Error log file
        self.error_log_file = self.log_dir / f"test_errors_{self.session_id}.log"
        
        # Azure OpenAI interaction log
        self.azure_log_file = self.log_dir / f"azure_interactions_{self.session_id}.log"
        
        # Setup logging handlers
        self._setup_logging_handlers()
    
    def _setup_logging_handlers(self):
        """Setup logging handlers for different types of logs."""
        # Main logger
        self.logger = logging.getLogger(f"test_session_{self.session_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # Main log handler
        main_handler = logging.FileHandler(self.main_log_file)
        main_handler.setLevel(logging.INFO)
        main_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        self.logger.addHandler(main_handler)
        
        # Error log handler
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        )
        error_handler.setFormatter(error_formatter)
        self.logger.addHandler(error_handler)
        
        # Azure OpenAI interaction logger
        self.azure_logger = logging.getLogger(f"azure_interactions_{self.session_id}")
        self.azure_logger.setLevel(logging.DEBUG)
        azure_handler = logging.FileHandler(self.azure_log_file)
        azure_handler.setLevel(logging.DEBUG)
        azure_formatter = logging.Formatter(
            '%(asctime)s - AZURE_OPENAI - %(levelname)s - %(message)s'
        )
        azure_handler.setFormatter(azure_formatter)
        self.azure_logger.addHandler(azure_handler)
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for logging."""
        import platform
        import sys
        
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd(),
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_test_start(self, test_name: str, stage_name: str):
        """Log test start."""
        self.logger.info(f"STARTING TEST: {test_name} in stage {stage_name}")
    
    def log_test_result(self, test_name: str, stage_name: str, status: str, 
                       duration: float, details: Dict[str, Any], 
                       error_message: Optional[str] = None,
                       error_traceback: Optional[str] = None,
                       request_data: Optional[Dict[str, Any]] = None,
                       response_data: Optional[Dict[str, Any]] = None,
                       azure_interaction: Optional[Dict[str, Any]] = None):
        """Log detailed test result."""
        
        # Create test log entry
        test_entry = TestLogEntry(
            timestamp=datetime.now().isoformat(),
            test_name=test_name,
            stage_name=stage_name,
            status=status,
            duration=duration,
            details=details,
            error_message=error_message,
            error_traceback=error_traceback,
            request_data=request_data,
            response_data=response_data,
            azure_openai_interaction=azure_interaction
        )
        
        # Add to current stage
        self.current_tests.append(test_entry)
        
        # Log to file
        if status == "FAILED" or status == "ERROR":
            self.logger.error(f"TEST FAILED: {test_name} - {error_message}")
            if error_traceback:
                self.logger.error(f"TRACEBACK: {error_traceback}")
        else:
            self.logger.info(f"TEST {status}: {test_name} ({duration:.2f}s)")
        
        # Log Azure OpenAI interaction if present
        if azure_interaction:
            self.log_azure_interaction(test_name, azure_interaction)
    
    def log_azure_interaction(self, test_name: str, interaction: Dict[str, Any]):
        """Log Azure OpenAI interaction details."""
        self.azure_logger.info(f"AZURE INTERACTION - Test: {test_name}")
        self.azure_logger.info(f"Request: {json.dumps(interaction.get('request', {}), indent=2)}")
        self.azure_logger.info(f"Response: {json.dumps(interaction.get('response', {}), indent=2)}")
        self.azure_logger.info(f"Duration: {interaction.get('duration', 0):.2f}s")
        self.azure_logger.info(f"Tokens Used: {interaction.get('tokens_used', 0)}")
        self.azure_logger.info("-" * 80)
    
    def start_stage(self, stage_name: str, stage_description: str):
        """Start logging a new stage."""
        self.current_tests = []
        self.logger.info(f"STARTING STAGE: {stage_name} - {stage_description}")
    
    def end_stage(self, stage_name: str, stage_description: str, 
                  total_tests: int, passed_tests: int, duration: float):
        """End logging a stage."""
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Create stage log entry
        stage_entry = StageLogEntry(
            timestamp=datetime.now().isoformat(),
            stage_name=stage_name,
            stage_description=stage_description,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            duration=duration,
            test_results=self.current_tests.copy()
        )
        
        self.stages.append(stage_entry)
        
        # Log stage summary
        self.logger.info(f"STAGE COMPLETED: {stage_name}")
        self.logger.info(f"  Tests: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
        self.logger.info(f"  Duration: {duration:.2f}s")
        
        if failed_tests > 0:
            self.logger.warning(f"  Failed tests: {failed_tests}")
    
    def end_session(self, total_tests: int, passed_tests: int, duration: float):
        """End logging the test session."""
        self.session_end_time = datetime.now()
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Create session log entry
        session_entry = SessionLogEntry(
            session_id=self.session_id,
            start_time=self.session_start_time.isoformat(),
            end_time=self.session_end_time.isoformat(),
            total_duration=duration,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            stages=self.stages,
            system_info=self.system_info,
            configuration=self._get_configuration()
        )
        
        # Save to JSON file
        self._save_session_to_json(session_entry)
        
        # Log session summary
        self.logger.info("=" * 80)
        self.logger.info("TEST SESSION COMPLETED")
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {passed_tests}")
        self.logger.info(f"Failed: {failed_tests}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(f"Total Duration: {duration:.2f}s")
        self.logger.info("=" * 80)
        
        # Generate detailed report
        self._generate_detailed_report(session_entry)
    
    def _get_configuration(self) -> Dict[str, Any]:
        """Get test configuration for logging."""
        from tests.config import config
        
        return {
            "base_url": config.BASE_URL,
            "api_base": config.API_BASE,
            "test_user_id": config.TEST_USER_ID,
            "request_timeout": config.REQUEST_TIMEOUT,
            "valid_claim_pdf": config.VALID_CLAIM_PDF,
            "expected_validation_score_min": config.EXPECTED_VALIDATION_SCORE_MIN,
            "expected_validation_score_max": config.EXPECTED_VALIDATION_SCORE_MAX
        }
    
    def _save_session_to_json(self, session_entry: SessionLogEntry):
        """Save complete session to JSON file."""
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(session_entry), f, indent=2, ensure_ascii=False)
    
    def _generate_detailed_report(self, session_entry: SessionLogEntry):
        """Generate detailed text report."""
        report_file = self.log_dir / f"detailed_report_{self.session_id}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LEGAL AGENT SYSTEM - DETAILED TEST REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # Session Information
            f.write("SESSION INFORMATION:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Session ID: {session_entry.session_id}\n")
            f.write(f"Start Time: {session_entry.start_time}\n")
            f.write(f"End Time: {session_entry.end_time}\n")
            f.write(f"Total Duration: {session_entry.total_duration:.2f}s\n")
            f.write(f"Success Rate: {session_entry.success_rate:.1f}%\n\n")
            
            # System Information
            f.write("SYSTEM INFORMATION:\n")
            f.write("-" * 40 + "\n")
            for key, value in session_entry.system_info.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Configuration
            f.write("TEST CONFIGURATION:\n")
            f.write("-" * 40 + "\n")
            for key, value in session_entry.configuration.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Stage-by-Stage Results
            f.write("STAGE-BY-STAGE RESULTS:\n")
            f.write("-" * 40 + "\n")
            for stage in session_entry.stages:
                f.write(f"\n{stage.stage_name}:\n")
                f.write(f"  Description: {stage.stage_description}\n")
                f.write(f"  Tests: {stage.passed_tests}/{stage.total_tests} passed ({stage.success_rate:.1f}%)\n")
                f.write(f"  Duration: {stage.duration:.2f}s\n")
                
                # Test details
                for test in stage.test_results:
                    status_icon = "✅" if test.status == "PASSED" else "❌"
                    f.write(f"    {status_icon} {test.test_name} ({test.duration:.2f}s)\n")
                    
                    if test.error_message:
                        f.write(f"      Error: {test.error_message}\n")
                    
                    if test.azure_openai_interaction:
                        f.write(f"      Azure OpenAI: {test.azure_openai_interaction.get('duration', 0):.2f}s, {test.azure_openai_interaction.get('tokens_used', 0)} tokens\n")
            
            # Failed Tests Summary
            failed_tests = []
            for stage in session_entry.stages:
                for test in stage.test_results:
                    if test.status in ["FAILED", "ERROR"]:
                        failed_tests.append((stage.stage_name, test))
            
            if failed_tests:
                f.write("\nFAILED TESTS DETAILS:\n")
                f.write("-" * 40 + "\n")
                for stage_name, test in failed_tests:
                    f.write(f"\nStage: {stage_name}\n")
                    f.write(f"Test: {test.test_name}\n")
                    f.write(f"Error: {test.error_message}\n")
                    if test.error_traceback:
                        f.write(f"Traceback: {test.error_traceback}\n")
                    f.write("-" * 20 + "\n")
            
            # Azure OpenAI Interactions Summary
            azure_interactions = []
            for stage in session_entry.stages:
                for test in stage.test_results:
                    if test.azure_openai_interaction:
                        azure_interactions.append((stage.stage_name, test))
            
            if azure_interactions:
                f.write("\nAZURE OPENAI INTERACTIONS:\n")
                f.write("-" * 40 + "\n")
                total_tokens = 0
                total_duration = 0
                for stage_name, test in azure_interactions:
                    interaction = test.azure_openai_interaction
                    tokens = interaction.get('tokens_used', 0)
                    duration = interaction.get('duration', 0)
                    total_tokens += tokens
                    total_duration += duration
                    
                    f.write(f"\nStage: {stage_name}\n")
                    f.write(f"Test: {test.test_name}\n")
                    f.write(f"Duration: {duration:.2f}s\n")
                    f.write(f"Tokens: {tokens}\n")
                    f.write("-" * 20 + "\n")
                
                f.write(f"\nTotal Azure OpenAI Usage:\n")
                f.write(f"  Total Duration: {total_duration:.2f}s\n")
                f.write(f"  Total Tokens: {total_tokens}\n")
    
    def get_log_files(self) -> Dict[str, str]:
        """Get paths to all log files."""
        return {
            "main_log": str(self.main_log_file),
            "json_log": str(self.json_log_file),
            "error_log": str(self.error_log_file),
            "azure_log": str(self.azure_log_file),
            "detailed_report": str(self.log_dir / f"detailed_report_{self.session_id}.txt")
        } 
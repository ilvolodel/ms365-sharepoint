"""Base operation class for MCP area-based operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OperationError(Exception):
    """Base exception for operation errors."""
    
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class BaseOperation(ABC):
    """Base class for all area-based operations."""
    
    def __init__(self, graph_client=None):
        """Initialize operation.
        
        Args:
            graph_client: (Deprecated) MicrosoftGraphClient instance - no longer used.
                         Operations now create GraphClient per request with access_token.
        """
        self.graph_client = graph_client  # Kept for backward compatibility
        self.area_name = self.__class__.__name__.replace("Operations", "").lower()
    
    @abstractmethod
    def get_supported_actions(self) -> List[str]:
        """Return list of supported actions for this operation area.
        
        Returns:
            List of action names (e.g., ["search", "get", "list"])
        """
        pass
    
    @abstractmethod
    def _validate_action_params(self, action: str, params: Dict) -> None:
        """Validate parameters for a specific action.
        
        Args:
            action: Action name
            params: Parameters dict
            
        Raises:
            OperationError: If validation fails
        """
        pass
    
    @abstractmethod
    def _execute_action(self, action: str, params: Dict) -> Any:
        """Execute a specific action.
        
        Args:
            action: Action name
            params: Validated parameters
            
        Returns:
            Action result data
            
        Raises:
            OperationError: If action fails
        """
        pass
    
    def execute(self, action: str, params: Dict) -> Dict:
        """Execute an action with validation and error handling.
        
        Args:
            action: Action to execute
            params: Action parameters
            
        Returns:
            Standardized response dict with success, data, metadata
        """
        try:
            # Validate action exists
            if action not in self.get_supported_actions():
                raise OperationError(
                    code="INVALID_ACTION",
                    message=f"Action '{action}' not supported in {self.area_name}_operations",
                    details={
                        "action": action,
                        "supported_actions": self.get_supported_actions()
                    }
                )
            
            # Validate parameters
            self._validate_action_params(action, params)
            
            # Execute action
            logger.info(f"Executing {self.area_name}.{action} with params: {list(params.keys())}")
            result = self._execute_action(action, params)
            
            # Return success response
            return self._format_response(
                success=True,
                data=result,
                action=action
            )
            
        except OperationError as e:
            logger.error(f"Operation error in {self.area_name}.{action}: {e.code} - {e.message}")
            return self._format_response(
                success=False,
                error={
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                },
                action=action
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error in {self.area_name}.{action}")
            return self._format_response(
                success=False,
                error={
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "details": {"type": type(e).__name__}
                },
                action=action
            )
    
    def _format_response(
        self,
        success: bool,
        action: str,
        data: Any = None,
        error: Optional[Dict] = None
    ) -> Dict:
        """Format standardized response.
        
        Args:
            success: Whether operation succeeded
            action: Action that was executed
            data: Result data (if success)
            error: Error dict (if failure)
            
        Returns:
            Standardized response dict
        """
        response = {
            "success": success,
            "metadata": {
                "action": action,
                "area": f"{self.area_name}_operations",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        if success:
            response["data"] = data
        else:
            response["error"] = error
        
        return response
    
    def _require_param(self, params: Dict, param_name: str, param_type: type = None) -> Any:
        """Validate required parameter exists and optionally check type.
        
        Args:
            params: Parameters dict
            param_name: Name of required parameter
            param_type: Expected type (optional)
            
        Returns:
            Parameter value
            
        Raises:
            OperationError: If parameter missing or wrong type
        """
        if param_name not in params:
            raise OperationError(
                code="MISSING_PARAM",
                message=f"Required parameter '{param_name}' not provided",
                details={"param": param_name}
            )
        
        value = params[param_name]
        
        if param_type is not None and not isinstance(value, param_type):
            raise OperationError(
                code="INVALID_PARAM_TYPE",
                message=f"Parameter '{param_name}' must be of type {param_type.__name__}",
                details={
                    "param": param_name,
                    "expected_type": param_type.__name__,
                    "actual_type": type(value).__name__
                }
            )
        
        return value
    
    def _validate_email(self, email: str) -> None:
        """Validate email address format.
        
        Args:
            email: Email address to validate
            
        Raises:
            OperationError: If email invalid
        """
        if not email or "@" not in email or "." not in email.split("@")[1]:
            raise OperationError(
                code="INVALID_EMAIL",
                message=f"Invalid email address: {email}",
                details={"email": email}
            )
    
    def _validate_datetime(self, dt_str: str, param_name: str = "datetime") -> None:
        """Validate ISO 8601 datetime string.
        
        Args:
            dt_str: Datetime string to validate
            param_name: Parameter name for error messages
            
        Raises:
            OperationError: If datetime invalid
        """
        try:
            # Try parsing as ISO 8601
            datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise OperationError(
                code="INVALID_DATETIME",
                message=f"Parameter '{param_name}' must be valid ISO 8601 datetime",
                details={
                    "param": param_name,
                    "value": dt_str,
                    "error": str(e)
                }
            )
    
    def _validate_choice(self, value: str, choices: List[str], param_name: str) -> None:
        """Validate value is one of allowed choices.
        
        Args:
            value: Value to validate
            choices: List of allowed values
            param_name: Parameter name for error messages
            
        Raises:
            OperationError: If value not in choices
        """
        if value not in choices:
            raise OperationError(
                code="INVALID_CHOICE",
                message=f"Parameter '{param_name}' must be one of: {', '.join(choices)}",
                details={
                    "param": param_name,
                    "value": value,
                    "allowed_values": choices
                }
            )

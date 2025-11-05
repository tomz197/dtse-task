from typing import Any, Dict, Optional


def success_response(data: Any = None) -> Dict[str, Any]:
    """
    Create a JSEND success response.

    Args:
        data: The data to return. Can be None, dict, list, or any serializable type.

    Returns:
        JSEND-compliant success response.
    """
    return {"status": "success", "data": data}


def fail_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a JSEND fail response for validation errors or invalid input.

    Args:
        data: Dictionary explaining what went wrong. Keys should correspond to
              input fields if validation errors, or descriptive error messages.

    Returns:
        JSEND-compliant fail response.
    """
    return {"status": "fail", "data": data}


def error_response(message: str, code: Optional[int] = None, data: Optional[Any] = None) -> Dict[str, Any]:
    """
    Create a JSEND error response for server errors.

    Args:
        message: A meaningful, end-user-readable message explaining what went wrong.
        code: Optional numeric error code.
        data: Optional additional error information (stack traces, conditions, etc.).

    Returns:
        JSEND-compliant error response.
    """
    response = {"status": "error", "message": message}

    if code is not None:
        response["code"] = code

    if data is not None:
        response["data"] = data

    return response

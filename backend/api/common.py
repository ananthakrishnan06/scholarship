"""Validated endpoints and sanitized, structured errors."""

from functools import wraps

from core.observability import event
from django.db import DatabaseError
from drf_spectacular.utils import extend_schema
from pydantic import ValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


def inline_schema(schema):
    """Expand Pydantic local definitions into a portable OpenAPI schema."""
    definitions = schema.get("$defs", {})

    def expand(value):
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            if "$ref" in value and value["$ref"].startswith("#/$defs/"):
                return expand(definitions[value["$ref"].split("/")[-1]])
            return {key: expand(item) for key, item in value.items() if key != "$defs"}
        return value

    return expand(schema)


def endpoint(method, schema=None, permissions=None, response_schema=None):
    def decorate(fn):
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            try:
                payload = schema.model_validate(request.data) if schema else None
                return fn(request, payload, *args, **kwargs)
            except ValidationError as exc:
                return Response(
                    {
                        "error": {
                            "code": "INVALID_INPUT",
                            "message": "Input validation failed.",
                            "fields": [
                                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                                for e in exc.errors()
                            ],
                        },
                        "request_id": request.request_id,
                    },
                    status=400,
                )
            except PermissionError:
                return Response(
                    {
                        "error": {
                            "code": "SESSION_ACCESS_DENIED",
                            "message": "Session not found or token invalid.",
                        }
                    },
                    status=404,
                )
            except ValueError as exc:
                return Response(
                    {"error": {"code": "INVALID_ARGUMENT", "message": str(exc)}}, status=400
                )
            except DatabaseError:
                event("database_failure", endpoint=request.path)
                return Response(
                    {
                        "error": {
                            "code": "DATABASE_UNAVAILABLE",
                            "message": "Persistent storage is unavailable.",
                        }
                    },
                    status=503,
                )
            except Exception as exc:
                event("request_failure", endpoint=request.path, error_type=type(exc).__name__)
                return Response(
                    {
                        "error": {
                            "code": "SERVICE_FAILURE",
                            "message": "Unable to complete the request.",
                            "request_id": request.request_id,
                        }
                    },
                    status=503,
                )

        if permissions:
            wrapped = permission_classes(permissions)(wrapped)
        view = api_view([method] if isinstance(method, str) else method)(wrapped)
        return extend_schema(
            request={"application/json": inline_schema(schema.model_json_schema())}
            if schema
            else None,
            responses={200: inline_schema(response_schema or {"type": "object"})},
            operation_id=fn.__name__ if isinstance(method, str) else None,
        )(view)

    return decorate

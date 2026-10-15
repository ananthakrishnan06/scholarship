"""Operational metadata and persistent private session/audit data."""

import uuid

from django.db import models


class Scholarship(models.Model):
    scheme_id = models.CharField(max_length=200, primary_key=True)
    name = models.CharField(max_length=300)
    corpus_hash = models.CharField(max_length=64)
    original_record_key = models.CharField(max_length=100)


class ScholarshipChunk(models.Model):
    chunk_id = models.CharField(max_length=250, primary_key=True)
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE)
    section = models.CharField(max_length=50)
    content_hash = models.CharField(max_length=64)


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ConversationMessage(models.Model):
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class AgentExecution(models.Model):
    session = models.ForeignKey(UserSession, null=True, on_delete=models.SET_NULL)
    request_id = models.CharField(max_length=64)
    status = models.CharField(max_length=40, default="RUNNING")
    latency_ms = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class ToolExecution(models.Model):
    execution = models.ForeignKey(AgentExecution, on_delete=models.CASCADE, related_name="tools")
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=40)
    attempt = models.PositiveIntegerField(default=1)
    latency_ms = models.FloatField()
    error_code = models.CharField(max_length=100, blank=True)


class LLMUsageLog(models.Model):
    execution = models.ForeignKey(
        AgentExecution, on_delete=models.CASCADE, related_name="llm_calls"
    )
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=150)
    phase = models.CharField(max_length=20, default="generation")
    input_tokens = models.PositiveIntegerField(null=True)
    output_tokens = models.PositiveIntegerField(null=True)
    total_tokens = models.PositiveIntegerField(null=True)
    estimated_cost = models.DecimalField(max_digits=16, decimal_places=8, null=True)
    status = models.CharField(max_length=40)
    latency_ms = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)


class EvaluationRun(models.Model):
    report = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

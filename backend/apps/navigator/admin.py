from django.contrib import admin

from apps.navigator.models import EvaluationRun, Scholarship

admin.site.register(Scholarship)
admin.site.register(EvaluationRun)

from django.contrib import admin
from .models import Contest, ContestClarification, ContestProblem

admin.site.register(Contest)
admin.site.register(ContestProblem)
admin.site.register(ContestClarification)
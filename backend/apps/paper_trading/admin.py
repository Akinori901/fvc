from django.contrib import admin

from .models import PaperPosition, PaperTrade

admin.site.register(PaperTrade)
admin.site.register(PaperPosition)

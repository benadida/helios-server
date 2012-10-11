from django.db import models

class Faculty(models.Model):
    name = models.CharField(max_length=255)
    faculty_id = models.CharField(max_length=255)


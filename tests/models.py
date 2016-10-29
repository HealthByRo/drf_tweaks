# -*- coding: utf-8 -*-
from django.db import models


class SampleModel(models.Model):
    a = models.CharField(max_length=50, null=True)
    b = models.CharField(max_length=50, null=True)

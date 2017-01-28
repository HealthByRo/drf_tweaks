# -*- coding: utf-8 -*-
from django.db import models


class SampleModel(models.Model):
    a = models.CharField(max_length=50, null=True)
    b = models.CharField(max_length=50, null=True)


class SampleModelForAutofilter(models.Model):
    fk = models.ForeignKey(SampleModel, related_name="fk_1", on_delete=models.CASCADE)
    non_indexed_fk = models.ForeignKey(SampleModel, related_name="fk_2", db_index=False, on_delete=models.CASCADE)
    indexed_int = models.IntegerField(db_index=True)
    non_indexed_int = models.IntegerField()
    indexed_char = models.CharField(max_length=255, db_index=True)
    non_indexed_char = models.CharField(max_length=255)
    indexed_text = models.TextField(db_index=True)
    non_indexed_text = models.TextField()
    indexed_url = models.URLField(db_index=True)
    non_indexed_url = models.URLField()
    indexed_email = models.EmailField(db_index=True)
    non_indexed_email = models.EmailField()
    nullable_field = models.IntegerField(null=True, db_index=True)

    @property
    def some_property(self):
        return "property"

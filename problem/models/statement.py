# from django.db import models
#
#
# class Statement(models.Model):
#   lang = models.CharField(choices=(
#     ("english", "English"),
#     ("chinese", "Chinese")
#   ), max_length=20)  # not used, yet
#   type = models.CharField(default="markdown", choices=(
#     ("tex", "TeX"),
#     ("markdown", "Markdown"),
#     ("html", "HTML"),
#     ("doc", "DOC"),
#     ("pdf", "PDF")
#   ))
#   encoding = models.CharField(max_length=20)
#   name = models.TextField(blank=True)
#   legend = models.TextField(blank=True)
#   input = models.TextField(blank=True)
#   output = models.TextField(blank=True)
#   interaction = models.TextField(blank=True)
#   notes = models.TextField(blank=True)
#   tutorial = models.TextField(blank=True)
#
#   packaged = models.BooleanField(default=False)
#
#   # render on the fly, results may be cached in the library with the following keys
#   create_time = models.DateTimeField(auto_now_add=True)
#   update_time = models.DateTimeField(auto_now=True)
#
#   class Meta:
#     ordering = ["packaged", "id"]

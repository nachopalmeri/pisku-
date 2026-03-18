# Django ORM

## Purpose
Django ORM patterns and best practices for building robust database-driven apps with Python.

## Models
```python
from django.db import models
from django.utils import timezone

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='posts')
    created_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['author', 'is_published'])]

    def __str__(self):
        return self.title
```

## Optimized QuerySets
```python
# select_related for ForeignKey (1 query)
posts = Post.objects.select_related('author').filter(is_published=True)

# prefetch_related for M2M / reverse FK (2 queries)
posts = Post.objects.prefetch_related('tags', 'comments').all()

# only() to limit columns
posts = Post.objects.only('title', 'created_at')

# annotate + aggregate
from django.db.models import Count, Avg
stats = Post.objects.annotate(comment_count=Count('comments')).aggregate(avg=Avg('comment_count'))

# F expressions (DB-level, no Python roundtrip)
from django.db.models import F
Post.objects.filter(is_published=True).update(view_count=F('view_count') + 1)
```

## Migrations
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
python manage.py sqlmigrate app_name 0001  # preview SQL
```

## Signals
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Post)
def notify_on_publish(sender, instance, created, **kwargs):
    if not created and instance.is_published:
        send_notification(instance)
```

## Admin Customization
```python
from django.contrib import admin

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'is_published', 'created_at']
    list_filter = ['is_published', 'author']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at']
    actions = ['publish_selected']

    def publish_selected(self, request, queryset):
        queryset.update(is_published=True)
```

## Key Patterns
- Use `select_related` for ForeignKey, `prefetch_related` for M2M
- `F()` for atomic DB updates
- `Q()` for complex OR/AND queries
- `bulk_create()` / `bulk_update()` for batch operations
- Index frequently filtered fields

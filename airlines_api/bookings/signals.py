from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Sector
from django.core.cache import cache

@receiver([post_save, post_delete], sender=Sector)
def invalidate_sector_cache(sender, **kwargs):

    print("Invalidating sector cache")

    cache.delete_pattern('*sector_list*')
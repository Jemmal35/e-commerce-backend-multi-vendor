from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db.models import Count, Avg

from .models import Review

def update_product_rating(product):
    stats = Review.objects.filter(product = product).aggregate(avg_rating = Avg('rating'), count = Count('id'))
    
    product.average_rating = round(stats['avg_rating'] or 0.00, 2)
    product.review_count = stats['count'] or 0
    
    product.save(update_fields = ['average_rating', 'review_count'])
    
    

@receiver(post_save, sender= Review)
def update_rating_on_save(sender, instance, created,  **kwargs):
    update_product_rating(instance.product)
    
@receiver(post_delete, sender= Review)
def update_rating_on_delete(sender, instance,  **kwargs):
    update_product_rating(instance.product)
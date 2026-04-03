from django.utils import timezone
from django.db.models import Avg, Count, F, Max
from .models import Order, OrderItem
from products.models import Product
from datetime import timedelta

class ReplenishmentService:
    @staticmethod
    def get_recommendations(shopkeeper):
        """
        Analyzes shopkeeper's purchase history to recommend products that need restocking.
        """
        # Get all distinct products this shopkeeper has ordered at least twice (to calculate frequency)
        past_orders = OrderItem.objects.filter(
            order__shopkeeper=shopkeeper
        ).values('product').annotate(
            order_count=Count('order', distinct=True),
            last_order_date=Max('order__created_at'),
            avg_quantity=Avg('quantity')
        ).filter(order_count__gt=1)

        recommendations = []
        now = timezone.now()

        for item in past_orders:
            product_id = item['product']
            if not product_id:
                continue
                
            # Get order dates for this product to calculate average interval
            order_dates = Order.objects.filter(
                shopkeeper=shopkeeper,
                items__product_id=product_id
            ).order_by('created_at').values_list('created_at', flat=True)

            intervals = []
            for i in range(len(order_dates) - 1):
                delta = order_dates[i+1] - order_dates[i]
                intervals.append(delta.total_seconds())

            if not intervals:
                continue

            avg_interval_seconds = sum(intervals) / len(intervals)
            avg_interval_days = avg_interval_seconds / 86400

            last_order_date = item['last_order_date']
            days_since_last_order = (now - last_order_date).total_seconds() / 86400

            # If we are at 80% or more of the typical interval, recommend it
            # Also don't recommend if it was ordered very recently (less than 1 day ago)
            if days_since_last_order >= (0.8 * avg_interval_days):
                product = Product.objects.get(id=product_id)
                recommendations.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'dealer_id': product.dealer.id,
                    'dealer_name': product.dealer.business_name if hasattr(product.dealer, 'business_name') else product.dealer.username,
                    'last_ordered_qty': int(item['avg_quantity']),
                    'days_since_last_order': round(days_since_last_order, 1),
                    'avg_cycle_days': round(avg_interval_days, 1),
                    'confidence': 'High' if days_since_last_order >= avg_interval_days else 'Medium',
                    'price': float(product.price)
                })

        # Sort by urgency (how close we are to the next cycle)
        return sorted(recommendations, key=lambda x: x['days_since_last_order'] / x['avg_cycle_days'] if x['avg_cycle_days'] > 0 else 0, reverse=True)

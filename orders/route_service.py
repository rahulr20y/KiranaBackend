from django.utils import timezone
from .models import Order
from shopkeepers.models import Shopkeeper
from decimal import Decimal
import math

class RouteService:
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Simplistic distance calculation (mocking Haversine for performance)"""
        if None in [lat1, lon1, lat2, lon2]:
            return 999999 # Far away
            
        return math.sqrt((Decimal(lat1) - Decimal(lat2))**2 + (Decimal(lon1) - Decimal(lon2))**2)

    @staticmethod
    def get_optimized_route(dealer_user):
        """
        Groups all 'shipped' orders for a dealer and sorts them into an optimized sequence.
        Uses a Greedy Nearest Neighbor approach starting from dealer location (or first shop).
        """
        # Fetch eligible orders (shipped but not delivered)
        orders = Order.objects.filter(
            dealer=dealer_user,
            status='shipped'
        ).select_related('shopkeeper__shopkeeper_profile')
        
        if not orders:
            return []
            
        # Extract stop data
        stops = []
        for order in orders:
            sk_profile = getattr(order.shopkeeper, 'shopkeeper_profile', None)
            stops.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'shop_name': sk_profile.shop_name if sk_profile else "Unknown Shop",
                'lat': sk_profile.latitude if sk_profile else None,
                'lon': sk_profile.longitude if sk_profile else None,
                'pincode': sk_profile.pincode if sk_profile else "000000",
                'address': sk_profile.address if sk_profile else order.shipping_address,
                'status': order.status
            })
            
        # Optimization: Simple Sort by Pincode then Lat/Lon (Clustering)
        # In a real app, we'd use a TSP solver, but for POC we use Geo-Clustering
        sorted_stops = sorted(stops, key=lambda x: (x['pincode'], x['lat'] or 0, x['lon'] or 0))
        
        # Update sequences in DB for persistence
        for idx, stop in enumerate(sorted_stops):
            Order.objects.filter(id=stop['order_id']).update(
                delivery_sequence=idx + 1,
                estimated_delivery_time=timezone.now() + timezone.timedelta(minutes=30 * (idx + 1))
            )
            stop['sequence'] = idx + 1
            stop['eta'] = (timezone.now() + timezone.timedelta(minutes=30 * (idx + 1))).isoformat()
            
        return sorted_stops

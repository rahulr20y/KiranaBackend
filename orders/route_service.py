from django.utils import timezone
from .models import Order
from shopkeepers.models import Shopkeeper
from decimal import Decimal
import math

class RouteService:
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """Standard distance calculation (Euclidean approximation for small distances)"""
        if None in [lat1, lon1, lat2, lon2]:
            return 999999 # Far away
            
        return math.sqrt((Decimal(lat1) - Decimal(lat2))**2 + (Decimal(lon1) - Decimal(lon2))**2)

    @staticmethod
    def get_optimized_route(dealer_user):
        """
        Groups all 'shipped' orders for a dealer and sorts them into an optimized sequence.
        Uses a Greedy Nearest Neighbor approach starting from dealer location.
        """
        dealer_profile = getattr(dealer_user, 'dealer_profile', None)
        start_lat = dealer_profile.latitude if dealer_profile else None
        start_lon = dealer_profile.longitude if dealer_profile else None

        # Fetch eligible orders (shipped but not delivered)
        orders = Order.objects.filter(
            dealer=dealer_user,
            status='shipped'
        ).select_related('shopkeeper__shopkeeper_profile')
        
        if not orders:
            return []
            
        # Extract stop data
        unvisited = []
        for order in orders:
            sk_profile = getattr(order.shopkeeper, 'shopkeeper_profile', None)
            unvisited.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'shop_name': sk_profile.shop_name if sk_profile else "Unknown Shop",
                'lat': sk_profile.latitude if sk_profile else None,
                'lon': sk_profile.longitude if sk_profile else None,
                'pincode': sk_profile.pincode if sk_profile else "000000",
                'address': sk_profile.address if sk_profile else order.shipping_address,
                'status': order.status
            })
            
        # Greedy Nearest Neighbor
        optimized_route = []
        curr_lat, curr_lon = start_lat, start_lon
        
        while unvisited:
            # Find nearest stop
            nearest_idx = 0
            min_dist = RouteService.calculate_distance(curr_lat, curr_lon, unvisited[0]['lat'], unvisited[0]['lon'])
            
            for i in range(1, len(unvisited)):
                dist = RouteService.calculate_distance(curr_lat, curr_lon, unvisited[i]['lat'], unvisited[i]['lon'])
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = i
            
            # Add to route and move
            next_stop = unvisited.pop(nearest_idx)
            optimized_route.append(next_stop)
            curr_lat, curr_lon = next_stop['lat'], next_stop['lon']

        # Update sequences in DB and enrich output
        for idx, stop in enumerate(optimized_route):
            Order.objects.filter(id=stop['order_id']).update(
                delivery_sequence=idx + 1,
                estimated_delivery_time=timezone.now() + timezone.timedelta(minutes=30 * (idx + 1))
            )
            stop['sequence'] = idx + 1
            stop['eta'] = (timezone.now() + timezone.timedelta(minutes=30 * (idx + 1))).isoformat()
            
        return optimized_route

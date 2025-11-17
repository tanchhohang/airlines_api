from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('users',views.UserViewSet)
router.register('sectors', views.SectorViewSet)
router.register('airlines', views.AirlinesViewSet)
router.register('passengers', views.PassengerViewSet)
router.register('bookings', views.BookingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.index, name="index"),
    path("book/", views.bookView, name="book"),
    path("search/", views.searchView, name="search"),
    path("route/<int:route_id>+<str:start_stop>+<str:end_stop>+<str:date>", views.bookingView, name="booking"),
    path("verification/<uuid:booking_id>", views.verificationView, name="verification"),
    path("accounts/passengerinfo/<uuid:booking_id>", views.passengerInfo, name="passengerinfo"),
    path("accounts/refund/<uuid:booking_id>", views.refundView, name="refund"),
    path("accounts/profile", views.profileView, name="profile"),
    path("accounts/balance", views.addBalanceView, name="balance"),
    path("accounts/bookings", views.bookingList, name="bookinglist"),
    path("accounts/transactions", views.transactionsView, name="transactions"),
]
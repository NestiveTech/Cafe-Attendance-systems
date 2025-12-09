from django.contrib import admin
from django.urls import path
from attendance import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('google-login/', views.google_login, name='google_login'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    
    # App
    path('', views.dashboard, name='dashboard'),
    path('employees/', views.employees_list, name='employees'),
    path('mark/', views.mark_attendance, name='mark_attendance'),
    
    # Reports
    path('report/daily/', views.trigger_daily_report, name='send_daily_report'),
    path('report/monthly/', views.trigger_monthly_report, name='send_monthly_report'),
]
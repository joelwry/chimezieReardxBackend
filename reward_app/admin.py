from .models import CustomUser, Payment, SurveyTask, Activity, Transaction
from django.contrib import admin

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'balance', 'date_joined','is_staff']
    readonly_fields = ['balance','password','email','is_staff','is_superuser']
    search_fields = ['username', 'email']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['customer__username', 'tx_hash']

@admin.register(SurveyTask)
class SurveyTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'reward_amount', 'is_active', 'deadline']
    search_fields = ['title']
    list_filter = ['type', 'is_active']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['task', 'reward_earned', 'completed', 'completed_at']
    search_fields = ['task']
    list_filter = ['task', 'customer','completed']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'type', 'amount','reference']
    search_fields = ['reference']
    list_filter = ['type', 'customer','created_at']

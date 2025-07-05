from .models import CustomUser, Payment, SurveyTask, Activity, DailyGrowthRate, DailyGrowth,Transaction,Reward, Withdrawal
from django.contrib import admin
from django.forms import ModelForm, ValidationError

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

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_reward']
    list_filter = ['user']
    search_fields = ['user']

# --- Admin for DailyGrowthRate ---
class DailyGrowthRateForm(ModelForm):
    """
    Custom form for DailyGrowthRate model to add validation rules.
    """
    class Meta:
        model = DailyGrowthRate
        fields = '__all__'

    def clean(self):
        """
        Custom validation for DailyGrowthRate fields.
        - Ensures min_amount is not zero or negative and is at least 1000.
        - Ensures min_amount is less than max_amount.
        """
        cleaned_data = super().clean()
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')

        # Validate min_amount is not zero/negative and is at least 1000
        if min_amount is not None:
            if min_amount <= 0:
                self.add_error('min_amount', "Minimum amount cannot be zero or negative.")
            if min_amount < 1000:
                self.add_error('min_amount', "Minimum amount must be at least 1000.")

        # Validate min_amount is less than max_amount
        if min_amount is not None and max_amount is not None:
            if min_amount >= max_amount:
                self.add_error('min_amount', "Minimum amount must be less than the maximum amount.")
                self.add_error('max_amount', "Maximum amount must be greater than the minimum amount.")

        return cleaned_data

@admin.register(DailyGrowthRate)
class DailyGrowthRateAdmin(admin.ModelAdmin):
    """
    Admin configuration for the DailyGrowthRate model.
    Uses a custom form for enhanced validation.
    """
    form = DailyGrowthRateForm
    list_display = ('name', 'min_amount', 'max_amount', 'rate')
    search_fields = ('name',)
    list_filter = ('rate',)


# --- Admin for DailyGrowth ---

@admin.register(DailyGrowth)
class DailyGrowthAdmin(admin.ModelAdmin):
    """
    Admin configuration for the DailyGrowth model.
    Restricts editing of sensitive fields and controls field visibility.
    """
    list_display = ('user', 'amount', 'rate', 'status', 'activated_date', 'claimed_date', 'days_active', 'grown_amount')
    list_filter = ('status', 'activated_date', 'claimed_date')
    search_fields = ('user__username', 'amount', 'status')
    
    # Define fields that should be read-only in the admin interface
    readonly_fields = ('user', 'rate', 'amount',  'days_active', 'grown_amount') #'activated_date',

    # Organize fields into fieldsets to control layout and readability
    fieldsets = (
        (None, {
            'fields': ('user', 'amount', 'rate', 'activated_date')
        }),
        ('Growth Details', {
            'fields': ('status', 'claimed_date')
        }),
        ('Calculated Fields', {
            'fields': ('days_active', 'grown_amount'),
            'description': 'These fields are calculated automatically and cannot be edited.'
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """
        Ensures 'claimed_date' is nullable in the form even if it's not set
        in the model, which helps with initial object creation if the field
        is not required immediately.
        """
        form = super().get_form(request, obj, **kwargs)
        if 'claimed_date' in form.base_fields:
            form.base_fields['claimed_date'].required = False
        return form

    # If you want to disable adding new DailyGrowth objects via admin, uncomment below
    # def has_add_permission(self, request):
    #     return False

    # The user can delete records by default. If you wanted to restrict deletion,
    # you would uncomment and modify the method below:
    # def has_delete_permission(self, request, obj=None):
    #     return super().has_delete_permission(request, obj)


admin.site.register(Withdrawal)
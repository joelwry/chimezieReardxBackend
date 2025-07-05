from rest_framework import serializers
from .models import Activity, Payment, SurveyTask,CustomUser, Transaction, Reward, DailyGrowthRate, DailyGrowth, Withdrawal
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import datetime

class SurveyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyTask
        fields = '__all__'

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'password', 'balance']
        read_only_fields = ['balance']
    '''
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
        )
        return user
    '''
    def create(self, validated_data):
        user = CustomUser(
            email=validated_data['email'],
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])  # 🔐 
        user.save()
        return user

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'created_at']

class ActivitySerializer(serializers.ModelSerializer):
    task = SurveyTaskSerializer(read_only=True)
    
    class Meta:
        model = Activity
        fields = '__all__'
        read_only_fields = ['reward_earned', 'completed_at', 'amount', 'rate', 'start_date', 'return_date', 'is_returned']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta : 
        model = Transaction
        fields = '__all__'
        read_only_fields = ['created_at'] # can still include Customer etc

class DashboardSerializer(serializers.Serializer):
    user_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    tasks_completed = serializers.IntegerField()
    available_tasks = serializers.IntegerField()
    balance_overview = serializers.ListField(child=serializers.DictField())
    available_tasks_list = SurveyTaskSerializer(many=True)
    recent_activity = ActivitySerializer(many=True)

class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = '__all__'

# --- Daily Growth Serializers ---
class DailyGrowthRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyGrowthRate
        fields = '__all__'

class DailyGrowthSerializer(serializers.ModelSerializer):
    plan = DailyGrowthRateSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(queryset=DailyGrowthRate.objects.all(), source='plan', write_only=True, required=True)
    grown_amount = serializers.SerializerMethodField()

    class Meta:
        model = DailyGrowth
        fields = ['id', 'user', 'plan', 'plan_id', 'amount', 'rate', 'status', 'activated_date', 'claimed_date', 'grown_amount']
        read_only_fields = ['user', 'status', 'activated_date', 'claimed_date', 'grown_amount']

    def get_grown_amount(self, obj):
        # Handle both model instances and dictionaries
        if hasattr(obj, 'grown_amount'):
            return round(obj.grown_amount(), 2)
        elif isinstance(obj, dict) and 'amount' in obj and 'rate' in obj:
            # Calculate grown amount for dictionary data
            amount = float(obj['amount'])
            rate = float(obj['rate'])
            
            # Get activated_date from obj or use current time
            if 'activated_date' in obj and obj['activated_date']:
                activated_date = obj['activated_date']
                if isinstance(activated_date, str):
                    activated_date = datetime.fromisoformat(activated_date.replace('Z', '+00:00'))
            else:
                activated_date = timezone.now()
            
            # Calculate days active
            end_date = timezone.now()
            if 'claimed_date' in obj and obj['claimed_date']:
                claimed_date = obj['claimed_date']
                if isinstance(claimed_date, str):
                    claimed_date = datetime.fromisoformat(claimed_date.replace('Z', '+00:00'))
                end_date = claimed_date
            
            days = (end_date.date() - activated_date.date()).days
            return round(amount * ((1 + rate / 100) ** days), 2)
        
        return 0.0

# --- Withdrawal Serializer ---
class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['id', 'user', 'amount', 'bank_name', 'account_name', 'account_number', 'status', 'created_at', 'processed_at', 'admin_notes']
        read_only_fields = ['user', 'status', 'created_at', 'processed_at', 'admin_notes']
